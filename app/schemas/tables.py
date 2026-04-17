from typing import Optional

from pydantic import BaseModel


class TableCreate(BaseModel):
    table_number: int
    capacity: int = 4
    label: Optional[str] = None
    zone_id: Optional[int] = None


class TableUpdate(BaseModel):
    table_number: Optional[int] = None
    capacity: Optional[int] = None
    label: Optional[str] = None
    status: Optional[str] = None


class TableResponse(BaseModel):
    table_id: int
    table_number: int
    table_code: str
    capacity: int
    status: str
    label: Optional[str] = None
    qr_code_url: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}
