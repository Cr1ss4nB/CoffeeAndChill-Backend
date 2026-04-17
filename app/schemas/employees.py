from typing import Optional

from pydantic import BaseModel, EmailStr


class EmployeeCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str
    phone: Optional[str] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    phone: Optional[str] = None


class EmployeeStatusUpdate(BaseModel):
    is_active: bool


class EmployeeResponse(BaseModel):
    employee_id: int
    full_name: str
    email: str
    role: str
    phone: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}
