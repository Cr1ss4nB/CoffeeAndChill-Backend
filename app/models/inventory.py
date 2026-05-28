from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from app.core.time import utc_now


class InventoryMovement(SQLModel, table=True):
    movement_id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.product_id")
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")
    movement_type: str = Field(max_length=20)  # IN|OUT|SALE|ADJUSTMENT|RETURN|WASTE
    quantity: int
    unit_cost: Optional[float] = Field(default=None, decimal_places=2)
    reason: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    related_order_id: Optional[int] = Field(default=None, foreign_key="order.order_id")
    movement_date: datetime = Field(default_factory=utc_now)


class Ingredient(SQLModel, table=True):
    ingredient_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    unit: str = Field(max_length=20)  # ml, g, units, kg, l
    description: Optional[str] = Field(default=None)
    min_stock: float = Field(default=0)
    is_active: bool = Field(default=True)

    stock_movements: Mapped[List["IngredientStockMovement"]] = Relationship(
        sa_relationship=relationship("IngredientStockMovement", back_populates="ingredient")
    )
    consumptions: Mapped[List["ProductConsumption"]] = Relationship(
        sa_relationship=relationship("ProductConsumption", back_populates="ingredient")
    )


class IngredientStockMovement(SQLModel, table=True):
    movement_id: int | None = Field(default=None, primary_key=True)
    ingredient_id: int = Field(foreign_key="ingredient.ingredient_id")
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")
    movement_type: str = Field(max_length=20)  # IN|OUT|SALE|WASTE|ADJUSTMENT
    quantity: float  # float to support fractional units (e.g. 250.5 ml)
    related_order_id: Optional[int] = Field(default=None, foreign_key="order.order_id")
    notes: Optional[str] = Field(default=None)
    movement_date: datetime = Field(default_factory=utc_now)

    ingredient: Mapped[Optional["Ingredient"]] = Relationship(
        sa_relationship=relationship("Ingredient", back_populates="stock_movements")
    )


class ProductConsumption(SQLModel, table=True):

    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.product_id")
    ingredient_id: int = Field(foreign_key="ingredient.ingredient_id")
    quantity_used: float  # quantity of ingredient consumed per 1 unit of product sold

    ingredient: Mapped[Optional["Ingredient"]] = Relationship(
        sa_relationship=relationship("Ingredient", back_populates="consumptions")
    )
