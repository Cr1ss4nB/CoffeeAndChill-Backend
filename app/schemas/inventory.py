from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AdjustmentReason(str, Enum):
    RECEIPT = "RECEIPT"
    WASTE = "WASTE"
    LOSS = "LOSS"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"


class AdjustmentRequest(BaseModel):
    product_id: int
    quantity: int
    reason: AdjustmentReason
    notes: Optional[str] = None


class MovementResponse(BaseModel):
    movement_id: int
    product_id: int
    product_name: str
    system_user_id: int
    user_name: str
    movement_type: str
    quantity: int
    unit_cost: Optional[float] = None
    reason: Optional[str] = None
    movement_date: str


class InventoryResponse(BaseModel):
    product_id: int
    name: str
    category: str
    price: float
    stock_quantity: int
    status: str
    is_low_stock: bool


class InventoryListResponse(BaseModel):
    items: list[InventoryResponse]
    total: int
    page: int
    limit: int
    low_stock_count: int
