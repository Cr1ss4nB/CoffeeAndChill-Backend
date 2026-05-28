from typing import Dict, List, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.redis import get_async_redis, get_redis_client
from app.schemas.auth import UserResponse
from app.schemas.order import CheckoutRequest, OrderItemResponse, OrderResponse
from app.services.order_service import process_checkout
from app.models.catalog import Product
from app.models.operations import Order
from app.models.infrastructure import TableSpot
import redis as sync_redis

router = APIRouter(tags=["orders"])


def _enrich_orders(orders: list, session: Session) -> List[OrderResponse]:
    table_ids = {o.table_id for o in orders if o.table_id}
    table_map: Dict[int, TableSpot] = {}
    if table_ids:
        tables = session.exec(select(TableSpot).where(TableSpot.table_id.in_(table_ids))).all()
        table_map = {t.table_id: t for t in tables}

    product_ids = {item.product_id for o in orders for item in o.items if item.product_id}
    product_map: Dict[int, str] = {}
    if product_ids:
        products = session.exec(select(Product).where(Product.product_id.in_(product_ids))).all()
        product_map = {p.product_id: p.name for p in products}

    result = []
    for o in orders:
        t = table_map.get(o.table_id) if o.table_id else None
        enriched_items = [
            OrderItemResponse(
                item_id=item.item_id,
                product_id=item.product_id,
                product_name=product_map.get(item.product_id) if item.product_id else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                status=item.status,
                special_instructions=item.special_instructions,
            )
            for item in o.items
        ]
        result.append(
            OrderResponse(
                order_id=o.order_id,
                customer_id=o.customer_id,
                table_id=o.table_id,
                table_number=t.table_number if t else None,
                table_code=t.table_code if t else None,
                order_type=o.order_type,
                status=o.status,
                total_amount=o.total_amount,
                order_date=o.order_date,
                notes=o.notes,
                items=enriched_items,
            )
        )
    return result


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(
        require_role(["admin", "employee", "waiter", "cashier"])
    ),
):
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.order_date.desc())
    )
    orders = session.exec(stmt).all()
    return _enrich_orders(orders, session)


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutRequest,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Recibe un carrito de compras, verifica precios/stock y crea la orden de manera transaccional.
    Solo disponible para usuarios autenticados.
    """
    order = process_checkout(session, payload, current_user)

    stmt = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.items))
    )
    order_with_items = session.exec(stmt).first()
    return _enrich_orders([order_with_items], session)[0]


VALID_TRANSITIONS = {
    "PENDING":   ["PREPARING", "CANCELLED"],
    "PREPARING": ["READY", "CANCELLED"],
    "READY":     ["DELIVERED"],
    "DELIVERED": [],
    "CANCELLED": [],
}


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: dict,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(
        require_role(["admin", "employee", "waiter", "cashier"])
    ),
    redis_client: sync_redis.Redis = Depends(get_redis_client),
):
    """
    Actualiza el estado de una orden.
    Valid Transitions: PENDING → PREPARING | CANCELLED
                      PREPARING → READY | CANCELLED
                      READY → DELIVERED
    Al marcar DELIVERED, la mesa asociada vuelve a FREE automáticamente.
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="El campo 'status' es requerido")

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se permite la transición de '{order.status}' a '{new_status}'. "
                   f"Estados válidos desde '{order.status}': {allowed}",
        )

    order.status = new_status
    session.add(order)

    if new_status == "DELIVERED" and order.table_id:
        table = session.get(TableSpot, order.table_id)
        if table:
            table.status = "FREE"
            session.add(table)

    session.commit()
    session.refresh(order)

    stmt = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.items))
    )
    refreshed = session.exec(stmt).first()
    enriched = _enrich_orders([refreshed], session)[0]

    try:
        redis_client.publish("orders:updates", enriched.model_dump_json())
    except Exception:
        pass  # SSE delivery is best-effort; DB is source of truth

    return enriched


@router.get("/stream")
async def orders_stream(
    current_user: UserResponse = Depends(
        require_role(["admin", "employee", "waiter", "cashier"])
    ),
    async_redis: aioredis.Redis = Depends(get_async_redis),
):
    """SSE stream de actualizaciones de pedidos para staff. Sin polling."""
    async def event_generator():
        pubsub = async_redis.pubsub()
        await pubsub.subscribe("orders:updates")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"data": message["data"]}
        finally:
            await pubsub.unsubscribe("orders:updates")

    return EventSourceResponse(event_generator())
