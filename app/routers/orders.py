from typing import List
from fastapi import APIRouter, Depends, status
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
    current_user: UserResponse = Depends(require_role(["admin", "employee", "waiter", "cashier"]))
):
    """
    Retorna todas las órdenes del sistema con sus respectivos items.
    Solo accesible para personal del establecimiento.
    """
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.order_date.desc())
    orders = session.exec(stmt).all()
    return orders


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutRequest,
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Recibe un carrito de compras, verifica precios/stock y crea la orden de manera transaccional.
    Solo disponible para usuarios autenticados.
    """
    order = process_checkout(session, payload, current_user)

    # Reload with items efficiently for the response model
    stmt = select(Order).where(Order.order_id == order.order_id).options(selectinload(Order.items))
    order_with_items = session.exec(stmt).first()

    return order_with_items
