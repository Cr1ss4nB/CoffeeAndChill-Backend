"""
Employee service layer for managing employees (SystemUsers) and their roles.

This service encapsulates all employee-related business logic,
including creation, updates, role assignment, and status management.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.security import Role, SystemUser

# Reusable messages
EMPLOYEE_NOT_FOUND = "Empleado no encontrado"


def create_employee(
    session: Session,
    data: Dict[str, Any]
) -> SystemUser:
    """
    Create a new employee with the given data.

    Args:
        session: Database session
        data: Dictionary containing employee information
              (full_name, email, password, role, phone)

    Returns:
        Created SystemUser instance

    Raises:
        HTTPException: If email already exists or role is invalid
    """
    # Validate required fields
    if not data.get("full_name") or not data.get("email") or not data.get("password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="full_name, email, and password are required"
        )

    # Check for duplicate email
    existing = session.exec(
        select(SystemUser).where(SystemUser.email == data["email"])
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado"
        )

    # Validate and get role
    role_name = data.get("role", "waiter")
    valid_roles = ["admin", "waiter", "cashier", "manager", "kitchen"]

    if role_name not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}"
        )

    role_obj = session.exec(
        select(Role).where(Role.role_name == role_name)
    ).first()

    if not role_obj:
        role_obj = Role(role_name=role_name, permissions="[]")
        session.add(role_obj)
        session.commit()
        session.refresh(role_obj)

    # Create employee
    employee = SystemUser(
        full_name=data["full_name"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
        role_id=role_obj.role_id,
        phone=data.get("phone"),
        is_active=True
    )

    session.add(employee)
    session.commit()
    session.refresh(employee)

    return employee


def update_employee(
    session: Session,
    employee_id: int,
    data: Dict[str, Any]
) -> SystemUser:
    """
    Update an existing employee's information.

    Args:
        session: Database session
        employee_id: ID of employee to update
        data: Dictionary with fields to update

    Returns:
        Updated SystemUser instance

    Raises:
        HTTPException: If employee not found or email conflict
    """
    employee = session.get(SystemUser, employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND
        )

    # Check email uniqueness if updating email
    if "email" in data and data["email"] != employee.email:
        existing = session.exec(
            select(SystemUser).where(SystemUser.email == data["email"])
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado"
            )
        employee.email = data["email"]

    # Update other fields
    if "full_name" in data:
        employee.full_name = data["full_name"]

    if "phone" in data:
        employee.phone = data["phone"]

    if "role" in data:
        role_name = data["role"]
        role = session.exec(
            select(Role).where(Role.role_name == role_name)
        ).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado"
            )
        employee.role_id = role.role_id

    if "password" in data:
        employee.password_hash = hash_password(data["password"])

    session.add(employee)
    session.commit()
    session.refresh(employee)

    return employee


def get_employee_with_role(
    session: Session,
    employee_id: int
) -> Dict[str, Any]:
    """
    Get employee details including role information.

    Args:
        session: Database session
        employee_id: ID of employee to retrieve

    Returns:
        Dictionary with employee and role details

    Raises:
        HTTPException: If employee not found
    """
    employee = session.get(SystemUser, employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND
        )

    return {
        "employee_id": employee.system_user_id,
        "full_name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "is_active": employee.is_active,
        "role": {
            "role_id": employee.role.role_id if employee.role else None,
            "role_name": employee.role.role_name if employee.role else None,
            "permissions": employee.role.permissions if employee.role else "[]"
        },
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "last_login": employee.last_login.isoformat() if employee.last_login else None
    }


def list_employees(
    session: Session,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """
    List all employees with optional filtering by active status.

    Args:
        session: Database session
        active_only: If True, only return active employees

    Returns:
        List of employee dictionaries with role info
    """
    stmt = select(SystemUser)

    if active_only:
        stmt = stmt.where(SystemUser.is_active == True)  # noqa: E712

    employees = session.exec(stmt).all()

    return [
        {
            "employee_id": e.system_user_id,
            "full_name": e.full_name,
            "email": e.email,
            "phone": e.phone,
            "is_active": e.is_active,
            "role": e.role.role_name if e.role else "unknown",
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in employees
    ]


def activate_employee(
    session: Session,
    employee_id: int
) -> SystemUser:
    """
    Activate an employee account.

    Args:
        session: Database session
        employee_id: ID of employee to activate

    Returns:
        Updated SystemUser instance

    Raises:
        HTTPException: If employee not found
    """
    employee = session.get(SystemUser, employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND
        )

    employee.is_active = True
    session.add(employee)
    session.commit()
    session.refresh(employee)

    return employee


def deactivate_employee(
    session: Session,
    employee_id: int
) -> SystemUser:
    """
    Deactivate an employee account.

    Args:
        session: Database session
        employee_id: ID of employee to deactivate

    Returns:
        Updated SystemUser instance

    Raises:
        HTTPException: If employee not found
    """
    employee = session.get(SystemUser, employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND
        )

    employee.is_active = False
    session.add(employee)
    session.commit()
    session.refresh(employee)

    return employee


def assign_role(
    session: Session,
    employee_id: int,
    role_id: int
) -> SystemUser:
    """
    Assign a role to an employee.

    Args:
        session: Database session
        employee_id: ID of employee
        role_id: ID of role to assign

    Returns:
        Updated SystemUser instance

    Raises:
        HTTPException: If employee or role not found
    """
    employee = session.get(SystemUser, employee_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EMPLOYEE_NOT_FOUND
        )

    role = session.get(Role, role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )

    employee.role_id = role_id
    session.add(employee)
    session.commit()
    session.refresh(employee)

    return employee
