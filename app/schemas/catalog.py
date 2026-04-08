from typing import Optional, List
from pydantic import BaseModel


class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    type: str
    description: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    product_id: int
    name: str
    category_id: int
    price: float
    stock_quantity: int
    status: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    category: CategoryResponse

    model_config = {"from_attributes": True}
