from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.security import hash_password
from app.models.security import Role, SystemUser
from app.schemas.auth import UserResponse
from app.schemas.employees import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)

router = APIRouter(prefix="/admin/employees", tags=["Employees"])


@router.get("", response_model=List[EmployeeResponse])
def get_employees(
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    employees = session.exec(
        select(SystemUser).where(SystemUser.is_active == True)
    ).all()
    return [
        EmployeeResponse(
            employee_id=e.system_user_id,
            full_name=e.full_name,
            email=e.email,
            role=e.role,
            phone=e.phone,
            is_active=e.is_active,
        )
        for e in employees
    ]


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: EmployeeCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    existing = session.exec(
        select(SystemUser).where(SystemUser.email == employee_data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado",
        )

    if employee_data.role not in ["admin", "waiter", "cashier"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol inválido. Debe ser admin, waiter o cashier",
        )

    role_obj = session.exec(
        select(Role).where(Role.role_name == employee_data.role)
    ).first()
    if not role_obj:
        role_obj = Role(role_name=employee_data.role, permissions="[]")
        session.add(role_obj)
        session.commit()
        session.refresh(role_obj)

    employee = SystemUser(
        full_name=employee_data.full_name,
        email=employee_data.email,
        password_hash=hash_password(employee_data.password),
        role_id=role_obj.role_id,
        phone=employee_data.phone,
        is_active=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)

    return EmployeeResponse(
        employee_id=employee.system_user_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.role_name if employee.role else employee_data.role,
        phone=employee.phone,
        is_active=employee.is_active,
    )


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("employees:manage")),
):
    employee = session.get(SystemUser, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado",
        )

    if employee_data.email:
        existing = session.exec(
            select(SystemUser).where(
                SystemUser.email == employee_data.email,
                SystemUser.system_user_id != employee_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado",
            )

    if employee_data.full_name is not None:
        employee.full_name = employee_data.full_name
    if employee_data.email is not None:
        employee.email = employee_data.email
    if employee_data.phone is not None:
        employee.phone = employee_data.phone
    if employee_data.role is not None:
        role_obj = session.exec(
            select(Role).where(Role.role_name == employee_data.role)
        ).first()
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado",
            )
        employee.role_id = role_obj.role_id

    session.commit()
    session.refresh(employee)

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
    employee = session.get(SystemUser, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado",
        )

    if employee.system_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta",
        )

    employee.is_active = status_data.is_active
    session.commit()
    session.refresh(employee)

    return EmployeeResponse(
        employee_id=employee.system_user_id,
        full_name=employee.full_name,
        email=employee.email,
        role=employee.role.role_name if employee.role else "unknown",
        phone=employee.phone,
        is_active=employee.is_active,
    )
