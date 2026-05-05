from typing import List, Optional

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
    image_url: Optional[str] = None
    fulfillment_type: str = "STOCK"  # STOCK | INGREDIENTS | BOTH (ver app.core.fulfillment.FulfillmentType)
    available_to_sell: int = 0
    max_units_by_ingredients: Optional[int] = None
    max_units_by_product_stock: int = 0
    ingredient_limited: bool = False

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductResponse):
    category: CategoryResponse

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    category_id: int
    price: float
    stock_quantity: int = 0
    description: Optional[str] = None
    status: str = "ACTIVE"
    image_url: Optional[str] = None
    fulfillment_type: str = "STOCK"


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None
    image_url: Optional[str] = None
    fulfillment_type: Optional[str] = None


class ProductStatusUpdate(BaseModel):
    status: str
