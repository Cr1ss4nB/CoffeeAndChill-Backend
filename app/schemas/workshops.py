from typing import Optional, List
from datetime import date, time
from pydantic import BaseModel


class WorkshopScheduleBase(BaseModel):
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int
    status: str = "OPEN"


class WorkshopScheduleCreate(WorkshopScheduleBase):
    pass


class WorkshopScheduleResponse(WorkshopScheduleBase):
    schedule_id: int
    workshop_id: int

    model_config = {"from_attributes": True}


class WorkshopBase(BaseModel):
    name: str
    category_id: int
    description: Optional[str] = None
    duration_minutes: int
    max_capacity: int
    price: float
    instructor_name: Optional[str] = None
    is_active: bool = True


class WorkshopCreate(WorkshopBase):
    schedules: Optional[List[WorkshopScheduleCreate]] = None


class WorkshopUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_capacity: Optional[int] = None
    price: Optional[float] = None
    instructor_name: Optional[str] = None
    is_active: Optional[bool] = None


class WorkshopResponse(WorkshopBase):
    workshop_id: int
    schedules: List[WorkshopScheduleResponse] = []

    model_config = {"from_attributes": True}