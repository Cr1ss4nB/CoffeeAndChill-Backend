from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class AdjustmentReason(str, Enum):
    RECEIPT = "RECEIPT"
    WASTE = "WASTE"
    LOSS = "LOSS"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"


# ── Ingredient schemas ────────────────────────────────────────────────────────

class IngredientCreate(BaseModel):
    name: str
    unit: str
    description: Optional[str] = None
    min_stock: float = 0


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    min_stock: Optional[float] = None
    is_active: Optional[bool] = None


class IngredientResponse(BaseModel):
    ingredient_id: int
    name: str
    unit: str
    description: Optional[str] = None
    min_stock: float
    is_active: bool
    current_stock: float = 0
    is_low_stock: bool = False

    model_config = {"from_attributes": True}


# ── ProductConsumption schemas ────────────────────────────────────────────────

class ConsumptionItem(BaseModel):
    ingredient_id: int
    quantity_used: float

    @field_validator("quantity_used")
    @classmethod
    def qty_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity_used must be > 0")
        return v


class ConsumptionUpsertRequest(BaseModel):
    """Replace all consumption entries for a product in one call."""
    items: list[ConsumptionItem]


class ConsumptionItemResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity_used: float

    model_config = {"from_attributes": True}


# ── IngredientStockMovement schemas ───────────────────────────────────────────

class IngredientAdjustmentRequest(BaseModel):
    ingredient_id: int
    quantity: float  # positive = IN, negative = OUT/WASTE
    reason: AdjustmentReason
    notes: Optional[str] = None


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


class MovementListResponse(BaseModel):
    items: list[MovementResponse]
    total: int
    page: int
    limit: int
