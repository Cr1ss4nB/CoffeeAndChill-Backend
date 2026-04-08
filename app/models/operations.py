from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Order(SQLModel, table=True):
    order_id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.customer_id")
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")
    table_id: Optional[int] = Field(default=None, foreign_key="tablespot.table_id")

    order_type: str  # DINE_IN|TAKEAWAY|DELIVERY|WORKSHOP|MIXED
    status: str = Field(default="PENDING")

    subtotal: float = Field(decimal_places=2)
    tax_amount: float = Field(default=0, decimal_places=2)
    discount_amount: float = Field(default=0, decimal_places=2)
    total_amount: float = Field(decimal_places=2)

    order_date: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None)

    items: List["OrderItem"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    item_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.order_id")

    product_id: Optional[int] = Field(default=None, foreign_key="product.product_id")
    reservation_id: Optional[int] = Field(
        default=None, foreign_key="workshopreservation.reservation_id")

    quantity: int
    unit_price: float = Field(decimal_places=2)
    subtotal: float = Field(decimal_places=2)

    item_type: str  # PRODUCT|WORKSHOP
    status: str = Field(default="PENDING")
    special_instructions: Optional[str] = Field(default=None)

    order: Order = Relationship(back_populates="items")


class Payment(SQLModel, table=True):
    payment_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.order_id")
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.customer_id")

    payment_method: str  # CASH|CARD|TRANSFER|WALLET|CRYPTO
    amount: float = Field(decimal_places=2)
    status: str = Field(default="PENDING")

    transaction_reference: Optional[str] = Field(default=None, max_length=100)
    tip_amount: float = Field(default=0, decimal_places=2)

    payment_date: datetime = Field(default_factory=datetime.utcnow)
    system_user_id: int = Field(foreign_key="systemuser.system_user_id")


class Invoice(SQLModel, table=True):
    invoice_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(unique=True, foreign_key="order.order_id")
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.customer_id")
    payment_id: Optional[int] = Field(default=None, foreign_key="payment.payment_id")

    invoice_type: str  # A|B|C|TICKET|CREDIT_NOTE
    invoice_number: str = Field(max_length=50, unique=True)
    tax_id: Optional[str] = Field(default=None, max_length=50)

    total_amount: float = Field(decimal_places=2)
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    pdf_url: Optional[str] = Field(default=None, max_length=255)
