from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.security import SystemUser
from app.schemas.auth import UserResponse
from app.schemas.employees import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.services.employee_service import EMPLOYEE_NOT_FOUND, activate_employee
from app.services.employee_service import create_employee as service_create_employee
from app.services.employee_service import deactivate_employee, get_employee_with_role
from app.services.employee_service import list_employees as service_list_employees
from app.services.employee_service import update_employee as service_update_employee

router = APIRouter(tags=["Employees"])


@router.get("", response_model=List[EmployeeResponse])
def get_employees(
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    """Get all employees with their roles."""
    employees = service_list_employees(session, active_only=False)
    return [
        EmployeeResponse(
            employee_id=e["employee_id"],
            full_name=e["full_name"],
            email=e["email"],
            role=e["role"],
            phone=e["phone"],
            is_active=e["is_active"],
        )
        for e in employees
    ]


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee_endpoint(
    employee_data: EmployeeCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    """Create a new employee."""
    data = {
        "full_name": employee_data.full_name,
        "email": employee_data.email,
        "password": employee_data.password,
        "role": employee_data.role,
        "phone": employee_data.phone,
    }

    employee = service_create_employee(session, data)

    return EmployeeResponse(
        employee_id=employee.system_user_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.role_name if employee.role else employee_data.role,
        phone=employee.phone,
        is_active=employee.is_active,
    )


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee_endpoint(
    employee_id: int,
    employee_data: EmployeeUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    """Update an existing employee."""
    update_dict = {}

    if employee_data.full_name is not None:
        update_dict["full_name"] = employee_data.full_name
    if employee_data.email is not None:
        update_dict["email"] = employee_data.email
    if employee_data.role is not None:
        update_dict["role"] = employee_data.role
    if employee_data.phone is not None:
        update_dict["phone"] = employee_data.phone

    employee = service_update_employee(session, employee_id, update_dict)

    return EmployeeResponse(
        employee_id=employee.system_user_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.role_name if employee.role else "unknown",
        phone=employee.phone,
        is_active=employee.is_active,
    )


@router.patch("/{employee_id}/status", response_model=EmployeeResponse)
def update_employee_status(
    employee_id: int,
    status_data: EmployeeStatusUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    """Update employee active status."""
    # Prevent user from deactivating their own account
    employee = session.get(SystemUser, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND,
        )

    if employee.system_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta",
        )

    # Use service to update status
    if status_data.is_active:
        employee = activate_employee(session, employee_id)
    else:
        employee = deactivate_employee(session, employee_id)

    return EmployeeResponse(
        employee_id=employee.system_user_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.role_name if employee.role else "unknown",
        phone=employee.phone,
        is_active=employee.is_active,
    )
