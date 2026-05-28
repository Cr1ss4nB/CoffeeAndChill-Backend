
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.time import utc_now


class Category(SQLModel, table=True):
    category_id: int | None = Field(default=None, primary_key=True)
    category_name: str = Field(max_length=50, unique=True)
    type: str = Field(max_length=20)  # PRODUCT|WORKSHOP
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)


class Product(SQLModel, table=True):
    product_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    category_id: int = Field(foreign_key="category.category_id")
    price: float = Field(decimal_places=2)
    stock_quantity: int = Field(default=0)
    # STOCK: solo límite por `stock_quantity` (sin receta o sin mezclar con insumos).
    # INGREDIENTS: cupo = receta; `stock_quantity` no limita.
    # BOTH: min(unidades de producto, min por insumos).
    fulfillment_type: str = Field(default="STOCK", max_length=20)
    status: str = Field(default="ACTIVE")
    description: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class RecipeItem(SQLModel, table=True):
    recipe_item_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.product_id")
    # ingredient_id refers to another Product that is marked as an ingredient (Insumo)
    ingredient_id: int = Field(foreign_key="product.product_id")
    quantity_needed: float = Field(default=1.0)
    unit: str = Field(default="ud", max_length=10)


class Workshop(SQLModel, table=True):
    workshop_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    category_id: int = Field(foreign_key="category.category_id")
    description: Optional[str] = Field(default=None)
    duration_minutes: int
    max_capacity: int
    price: float = Field(decimal_places=2)
    instructor_name: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)


class WorkshopSchedule(SQLModel, table=True):
    schedule_id: int | None = Field(default=None, primary_key=True)
    workshop_id: int = Field(foreign_key="workshop.workshop_id")
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int
    status: str = Field(default="OPEN")
