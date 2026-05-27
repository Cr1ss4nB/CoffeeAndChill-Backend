from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped
from sqlmodel import Column, Field, Relationship, SQLModel

from app.core.time import utc_now


class Customer(SQLModel, table=True):
    customer_id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=100, unique=True)
    phone: Optional[str] = Field(default=None, max_length=20)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    birth_date: Optional[date] = Field(default=None)
    loyalty_points: int = Field(default=0)
    is_registered: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    reservations: Mapped[List["WorkshopReservation"]] = Relationship(back_populates="customer")


class WorkshopReservation(SQLModel, table=True):
    reservation_id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.customer_id")
    schedule_id: int = Field(foreign_key="workshopschedule.schedule_id")
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")
    quantity_slots: int = Field(default=1)
    total_price: Optional[float] = Field(default=None, decimal_places=2)
    status: str = Field(default="PENDING")
    reservation_date: datetime = Field(default_factory=utc_now)
    special_requests: Optional[str] = Field(default=None)

    customer: Mapped[Customer] = Relationship(back_populates="reservations")


class Notification(SQLModel, table=True):
    notification_id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.customer_id")
    related_order_id: Optional[int] = Field(default=None, foreign_key="order.order_id")
    notification_type: str = Field(max_length=50)
    message: str
    channel: str = Field(max_length=20)  # EMAIL|SMS|WHATSAPP|PUSH
    status: str = Field(default="PENDING")
    sent_at: Optional[datetime] = Field(default=None)
    read_at: Optional[datetime] = Field(default=None)


class ActivityLog(SQLModel, table=True):
    log_id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.customer_id")
    activity_type: str = Field(max_length=50)
    related_order_id: Optional[int] = Field(default=None, foreign_key="order.order_id")
    related_payment_id: Optional[int] = Field(default=None, foreign_key="payment.payment_id")
    activity_date: datetime = Field(default_factory=utc_now)
    activity_metadata: Optional[Any] = Field(default=None, sa_column=Column(JSON))
