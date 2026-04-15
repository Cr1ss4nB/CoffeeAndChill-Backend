from typing import Optional

from pydantic import BaseModel


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
