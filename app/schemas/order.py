from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, description="La cantidad debe ser mayor a cero")
    special_instructions: Optional[str] = None


class CheckoutRequest(BaseModel):
    order_type: str = Field(pattern="^(DINE_IN|TAKEAWAY|DELIVERY)$", description="Tipo de orden")
    table_id: Optional[int] = None
    notes: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1, description="El carrito no puede estar vacío")


class OrderItemResponse(BaseModel):
    item_id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float
    status: str

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    order_id: int
    customer_id: Optional[int] = None
    order_type: str
    status: str
    total_amount: float
    order_date: datetime
    items: List[OrderItemResponse]

    model_config = {"from_attributes": True}
