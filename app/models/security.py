from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Role(SQLModel, table=True):
    role_id: Optional[int] = Field(default=None, primary_key=True)
    role_name: str = Field(max_length=50, unique=True, index=True)
    permissions: Optional[str] = Field(default=None)  # stored as JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)

    users: List["SystemUser"] = Relationship(back_populates="role")


class SystemUser(SQLModel, table=True):
    system_user_id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    email: str = Field(max_length=100, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role_id: int = Field(foreign_key="role.role_id")
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)

    role: Optional[Role] = Relationship(back_populates="users")
