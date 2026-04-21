from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class InventoryMovement(SQLModel, table=True):
    movement_id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.product_id")
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")
    movement_type: str = Field(max_length=20)  # IN|OUT|SALE|ADJUSTMENT|RETURN|WASTE
    quantity: int
    unit_cost: Optional[float] = Field(default=None, decimal_places=2)
    reason: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    related_order_id: Optional[int] = Field(default=None, foreign_key="order.order_id")
    movement_date: datetime = Field(default_factory=datetime.utcnow)
