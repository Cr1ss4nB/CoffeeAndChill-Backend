from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Mapped, relationship
from sqlmodel import Field, Relationship, SQLModel


class TableZone(SQLModel, table=True):
    zone_id: int | None = Field(default=None, primary_key=True)
    zone_name: str = Field(max_length=50, unique=True)
    zone_type: str = Field(max_length=20)  # BAR|FLOOR|OUTDOOR|VIP
    floor_number: int = Field(default=1)
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(default=None)

    spots: Mapped[List["TableSpot"]] = Relationship(
        sa_relationship=relationship("TableSpot", back_populates="zone")
    )


class TableSpot(SQLModel, table=True):
    table_id: int | None = Field(default=None, primary_key=True)
    zone_id: int | None = Field(default=None, foreign_key="tablezone.zone_id")
    table_number: int
    table_code: str = Field(max_length=10, unique=True)
    capacity: int = Field(default=4)
    status: str = Field(default="FREE")  # FREE|OCCUPIED|RESERVED|MAINTENANCE
    qr_code_url: Optional[str] = Field(default=None, max_length=255)
    label: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)

    zone: Mapped[Optional["TableZone"]] = Relationship(
        sa_relationship=relationship("TableZone", back_populates="spots")
    )
