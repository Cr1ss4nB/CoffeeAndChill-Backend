from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.order import CheckoutRequest, OrderResponse
from app.services.order_service import process_checkout

router = APIRouter(prefix="/orders", tags=["orders"])

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
    from sqlmodel import select
    from app.models.operations import Order
    
    stmt = select(Order).where(Order.order_id == order.order_id).options(selectinload(Order.items))
    order_with_items = session.exec(stmt).first()
    
    return order_with_items
