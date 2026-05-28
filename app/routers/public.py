import json
from typing import List, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.redis import get_async_redis
from app.models.infrastructure import TableSpot
from app.models.catalog import Product, Category
from app.models.operations import Order
from app.models.security import SystemUser
from app.schemas.order import CheckoutRequest, OrderItemCreate, OrderItemResponse, OrderResponse
from app.services.availability import compute_sellable_snapshot

router = APIRouter(tags=["public"])


class TableInfoResponse(BaseModel):
    table_id: int
    table_number: int
    table_code: str
    label: Optional[str]
    status: str
    capacity: int

    model_config = {"from_attributes": True}


class PublicCheckoutRequest(BaseModel):
    table_code: Optional[str] = None
    order_type: str = Field(default="DINE_IN", pattern="^(DINE_IN|TAKEAWAY)$")
    items: List[OrderItemCreate]
    notes: Optional[str] = None


class PublicOrderStatus(BaseModel):
    order_id: int
    status: str
    order_type: str
    total_amount: float
    notes: Optional[str] = None
    items: List[OrderItemResponse]

    model_config = {"from_attributes": True}


@router.get("/tables/{table_code}", response_model=TableInfoResponse)
def get_table_by_code(
    table_code: str,
    session: Session = Depends(get_db),
):
    """
    Retorna información de una mesa por su código.
    Sin auth — público para clientes QR.
    """
    table = session.exec(
        select(TableSpot).where(TableSpot.table_code == table_code)
    ).first()

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada",
        )

    if not table.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no disponible",
        )

    if table.status == "MAINTENANCE":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Esta mesa no está disponible en este momento",
        )

    return table


@router.get("/menu")
def get_public_menu(
    category_id: Optional[int] = None,
    session: Session = Depends(get_db),
):
    """
    Retorna el catálogo de productos activos para clientes públicos.
    Soporta filtro opcional por categoría.
    """
    query = (
        select(Product, Category.category_name)
        .join(Category, Product.category_id == Category.category_id)
        .where(Product.status == "ACTIVE")
        .order_by(Category.category_name, Product.name)
    )

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    results = session.exec(query).all()

    menu = []
    for product, category_name in results:
        snap = compute_sellable_snapshot(session, product)
        menu.append({
            "product_id": product.product_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "category_id": product.category_id,
            "category_name": category_name,
            "image_url": product.image_url,
            "status": product.status,
            "available_to_sell": snap["available_to_sell"],
        })

    return menu


@router.get("/tables", response_model=List[TableInfoResponse])
def list_public_tables(session: Session = Depends(get_db)):
    """Lista mesas activas y disponibles — para selector en checkout sin QR."""
    tables = session.exec(
        select(TableSpot)
        .where(TableSpot.is_active == True)
        .where(TableSpot.status != "MAINTENANCE")
        .order_by(TableSpot.table_number)
    ).all()
    return tables


@router.post("/orders", response_model=PublicOrderStatus, status_code=status.HTTP_201_CREATED)
def place_public_order(
    payload: PublicCheckoutRequest,
    session: Session = Depends(get_db),
):
    """
    Crea una orden desde el menú público (sin auth).
    - Con table_code (QR): valida mesa, marca OCCUPIED, DINE_IN.
    - Sin table_code + TAKEAWAY: orden sin mesa, para llevar.
    - Sin table_code + DINE_IN: orden sin mesa, mesero asigna al llegar.
    """
    table = None
    table_id = None

    if payload.table_code:
        table = session.exec(
            select(TableSpot).where(TableSpot.table_code == payload.table_code)
        ).first()

        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa no encontrada",
            )
        if not table.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa no disponible",
            )
        if table.status == "MAINTENANCE":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Esta mesa no está disponible en este momento",
            )
        table_id = table.table_id

    admin = session.exec(
        select(SystemUser).where(SystemUser.is_active == True)
    ).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No hay usuario de sistema activo para registrar la venta",
        )

    mock_user = type("obj", (object,), {
        "id": admin.system_user_id,
        "role": "admin",
    })()

    checkout_data = CheckoutRequest(
        order_type=payload.order_type,
        table_id=table_id,
        notes=payload.notes,
        items=payload.items,
    )

    from app.services.order_service import process_checkout
    order = process_checkout(session, checkout_data, mock_user)

    if table:
        table.status = "OCCUPIED"
        session.add(table)
    session.commit()

    stmt = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.items))
    )
    refreshed = session.exec(stmt).first()
    return PublicOrderStatus.model_validate(refreshed)


@router.get("/orders/{order_id}", response_model=PublicOrderStatus)
def get_public_order_status(
    order_id: int,
    session: Session = Depends(get_db),
):
    """
    Retorna el estado actual de un pedido para el cliente QR.
    Sin auth — solo requiere order_id.
    """
    stmt = (
        select(Order)
        .where(Order.order_id == order_id)
        .options(selectinload(Order.items))
    )
    order = session.exec(stmt).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    product_ids = {item.product_id for item in order.items if item.product_id}
    product_map: dict = {}
    if product_ids:
        products = session.exec(select(Product).where(Product.product_id.in_(product_ids))).all()
        product_map = {p.product_id: p.name for p in products}

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
        for item in order.items
    ]
    return PublicOrderStatus(
        order_id=order.order_id,
        status=order.status,
        order_type=order.order_type,
        total_amount=order.total_amount,
        notes=order.notes,
        items=enriched_items,
    )


@router.get("/orders/{order_id}/stream")
async def public_order_stream(
    order_id: int,
    async_redis: aioredis.Redis = Depends(get_async_redis),
):
    """SSE stream de status para el cliente QR. Sin auth."""
    async def event_generator():
        pubsub = async_redis.pubsub()
        await pubsub.subscribe("orders:updates")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    if data.get("order_id") == order_id:
                        yield {"data": message["data"]}
        finally:
            await pubsub.unsubscribe("orders:updates")

    return EventSourceResponse(event_generator())