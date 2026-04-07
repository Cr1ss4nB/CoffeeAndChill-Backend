from datetime import datetime, date, time
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Category(SQLModel, table=True):
    category_id: Optional[int] = Field(default=None, primary_key=True)
    category_name: str = Field(max_length=50, unique=True)
    type: str = Field(max_length=20)  # PRODUCT|WORKSHOP
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)

    products: List["Product"] = Relationship(back_populates="category")
    workshops: List["Workshop"] = Relationship(back_populates="category")

class Product(SQLModel, table=True):
    product_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    category_id: int = Field(foreign_key="category.category_id")
    price: float = Field(decimal_places=2)
    stock_quantity: int = Field(default=0)
    status: str = Field(default="ACTIVE")
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    category: Category = Relationship(back_populates="products")

class Workshop(SQLModel, table=True):
    workshop_id: Optional[int] = Field(default=None, primary_key=True)
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
    schedule_id: Optional[int] = Field(default=None, primary_key=True)
    workshop_id: int = Field(foreign_key="workshop.workshop_id")
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int
    status: str = Field(default="OPEN")

    workshop: Workshop = Relationship(back_populates="schedules")
