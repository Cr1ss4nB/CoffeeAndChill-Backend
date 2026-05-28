import json
import os
from typing import List

import qrcode
import redis as sync_redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission, require_role
from app.core.redis import get_redis_client
from app.models.catalog import Product
from app.models.infrastructure import TableSpot
from app.models.operations import Order, Payment
from app.schemas.auth import UserResponse
from app.schemas.order import OrderItemResponse, OrderResponse
from app.schemas.tables import TableCreate, TableResponse, TableUpdate


class TableCloseRequest(BaseModel):
    payment_method: str  # CASH|CARD|TRANSFER|WALLET
    tip_amount: float = 0.0

router = APIRouter(tags=["Tables"])


@router.get("", response_model=List[TableResponse])
def get_tables(
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    tables = session.exec(select(TableSpot).where(TableSpot.is_active == True)).all()
    print(f"DEBUG: El servidor encontró {len(tables)} mesas activas.")
    return tables


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    table_data: TableCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    existing = session.exec(
        select(TableSpot).where(TableSpot.table_number == table_data.table_number)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número de mesa ya está en uso",
        )

    table_code = f"T{table_data.table_number:03d}"

    table = TableSpot(
        table_number=table_data.table_number,
        table_code=table_code,
        capacity=table_data.capacity,
        label=table_data.label,
        status="FREE",
        is_active=True,
    )
    session.add(table)
    session.commit()
    session.refresh(table)

    return table


@router.put("/{table_id}", response_model=TableResponse)
def update_table(
    table_id: int,
    table_data: TableUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    if table_data.table_number is not None:
        existing = session.exec(
            select(TableSpot).where(
                TableSpot.table_number == table_data.table_number,
                TableSpot.table_id != table_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El número de mesa ya está en uso",
            )
        table.table_number = table_data.table_number
        table.table_code = f"T{table_data.table_number:03d}"

    if table_data.capacity is not None:
        table.capacity = table_data.capacity
    if table_data.label is not None:
        table.label = table_data.label
    if table_data.status is not None:
        if table_data.status not in ["FREE", "OCCUPIED", "RESERVED", "MAINTENANCE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado inválido",
            )
        table.status = table_data.status

    session.commit()
    session.refresh(table)

    return table


@router.delete("/{table_id}")
def delete_table(
    table_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    table.is_active = False
    session.commit()

    return {"message": "Mesa desactivada exitosamente"}


@router.post("/{table_id}/close")
def close_table(
    table_id: int,
    payload: TableCloseRequest,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role(["admin", "employee", "cashier"])),
    redis_client: sync_redis.Redis = Depends(get_redis_client),
):
    """
    Cierra una mesa: marca todas sus órdenes activas como DELIVERED,
    registra el pago y libera la mesa a FREE.
    """
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa no encontrada")
    if table.status != "OCCUPIED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La mesa no está ocupada")

    active_orders = session.exec(
        select(Order)
        .where(
            Order.table_id == table_id,
            Order.status.not_in(["DELIVERED", "CANCELLED"]),
        )
        .options(selectinload(Order.items))
    ).all()

    total = sum(o.total_amount for o in active_orders) if active_orders else 0.0

    for order in active_orders:
        order.status = "DELIVERED"

    payment = None
    if active_orders:
        payment = Payment(
            order_id=active_orders[0].order_id,
            payment_method=payload.payment_method,
            amount=total,
            tip_amount=payload.tip_amount,
            status="COMPLETED",
            system_user_id=current_user.id,
        )
        session.add(payment)

    table.status = "FREE"
    session.commit()

    if active_orders:
        session.refresh(payment)

    # Batch-load products for SSE publish
    product_ids = {item.product_id for o in active_orders for item in o.items if item.product_id}
    product_map: dict = {}
    if product_ids:
        prods = session.exec(select(Product).where(Product.product_id.in_(product_ids))).all()
        product_map = {p.product_id: p.name for p in prods}

    for order in active_orders:
        session.refresh(order)
        enriched_items = [
            OrderItemResponse(
                item_id=item.item_id,
                product_id=item.product_id,
                product_name=product_map.get(item.product_id) if item.product_id else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                status=item.status,
            )
            for item in order.items
        ]
        order_resp = OrderResponse(
            order_id=order.order_id,
            customer_id=order.customer_id,
            table_id=order.table_id,
            table_number=table.table_number,
            table_code=table.table_code,
            order_type=order.order_type,
            status=order.status,
            total_amount=order.total_amount,
            order_date=order.order_date,
            items=enriched_items,
        )
        try:
            redis_client.publish("orders:updates", order_resp.model_dump_json())
        except Exception:
            pass

    return {
        "payment_id": payment.payment_id if payment else None,
        "order_ids": [o.order_id for o in active_orders],
        "total_amount": total,
        "tip_amount": payload.tip_amount,
        "payment_method": payload.payment_method,
        "table_id": table_id,
    }


@router.get("/{table_id}/qr")
def generate_table_qr(
    table_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("tables:manage")),
):
    """
    Genera y retorna una imagen PNG con el QR de la mesa.
    El QR apunta a {FRONTEND_URL}/menu/{table_code}.
    """
    table = session.get(TableSpot, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    qr_url = f"{frontend_url}/menu/{table.table_code}"

    qr_dir = "/app/media/qr"
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, f"{table.table_code}.png")

    qr_img = qrcode.make(qr_url)
    qr_img.save(qr_path)

    table.qr_code_url = f"/media/qr/{table.table_code}.png"
    session.add(table)
    session.commit()

    return FileResponse(qr_path, media_type="image/png")
