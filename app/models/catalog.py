from __future__ import annotations
from datetime import date, datetime, time
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utc_now


class Category(SQLModel, table=True):
    category_id: int | None = Field(default=None, primary_key=True)
    category_name: str = Field(max_length=50, unique=True)
    type: str = Field(max_length=20)  # PRODUCT|WORKSHOP
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)

    products: List["Product"] = Relationship(back_populates="category")
    workshops: List["Workshop"] = Relationship(back_populates="category")


class Product(SQLModel, table=True):
    role_id: int | None = Field(default=None, primary_key=True)
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

    category: Category = Relationship(back_populates="products")
    # This relationship represents the ingredients needed for THIS product
    recipe_items: List["RecipeItem"] = Relationship(
        back_populates="product", 
        sa_relationship_kwargs={"foreign_keys": "[RecipeItem.product_id]"}
    )
    # This relationship represents where THIS product is used as an ingredient
    used_in_recipes: List["RecipeItem"] = Relationship(
        back_populates="ingredient",
        sa_relationship_kwargs={"foreign_keys": "[RecipeItem.ingredient_id]"}
    )


class RecipeItem(SQLModel, table=True):
    recipe_item_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.product_id")
    # ingredient_id refers to another Product that is marked as an ingredient (Insumo)
    ingredient_id: int = Field(foreign_key="product.product_id")
    quantity_needed: float = Field(default=1.0)
    unit: str = Field(default="ud", max_length=10)

    product: Product = Relationship(
        back_populates="recipe_items", 
        sa_relationship_kwargs={"foreign_keys": "[RecipeItem.product_id]"}
    )
    ingredient: Product = Relationship(
        back_populates="used_in_recipes",
        sa_relationship_kwargs={"foreign_keys": "[RecipeItem.ingredient_id]"}
    )


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

    category: Category = Relationship(back_populates="workshops")
    schedules: List["WorkshopSchedule"] = Relationship(back_populates="workshop")


class WorkshopSchedule(SQLModel, table=True):
    system_user_id: int | None = Field(default=None, primary_key=True)
    workshop_id: int = Field(foreign_key="workshop.workshop_id")
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int
    status: str = Field(default="OPEN")

    workshop: Workshop = Relationship(back_populates="schedules")
