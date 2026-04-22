from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.schemas.auth import UserResponse
from app.schemas.order import CheckoutRequest, OrderResponse
from app.services.order_service import process_checkout
from app.models.operations import Order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(
        require_role(["admin", "employee", "waiter", "cashier"])
    ),
):
    """
    Retorna todas las órdenes del sistema con sus respectivos items.
    Solo accesible para personal del establecimiento.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.order_date.desc())
    )
    orders = session.exec(stmt).all()
    return orders


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

    # Reload with items efficiently for the response model
    stmt = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.items))
    )
    order_with_items = session.exec(stmt).first()

    return order_with_items


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: dict,  # Expected {"status": "NEW_STATUS"}
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(
        require_role(["admin", "employee", "waiter", "cashier"])
    ),
):
    """
    Actualiza el estado de una orden.
    """
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="El campo 'status' es requerido")

    order.status = new_status
    session.add(order)
    session.commit()
    session.refresh(order)

    # Reload with items
    stmt = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.items))
    )
    return session.exec(stmt).first()
