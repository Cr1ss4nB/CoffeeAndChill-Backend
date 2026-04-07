from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
)
from app.models.crm import Customer
from app.models.security import SystemUser
from app.schemas.auth import CustomerRegister, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(id: int, name: str, email: str, role: str) -> UserResponse:
    return UserResponse(id=id, name=name, email=email, role=role)


# ── POST /auth/register ────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: CustomerRegister, session: Session = Depends(get_session)):
    """Register a new client account."""
    existing = session.exec(
        select(Customer).where(Customer.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email",
        )

    customer = Customer(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_registered=True,
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return _user_response(
        id=customer.customer_id,
        name=customer.full_name,
        email=customer.email,
        role="client",
    )


# ── POST /auth/login ───────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    """
    Unified login. Checks system_user (admin/employee) first, then customer.
    Returns JWT access + refresh tokens.
    """
    # 1. Try system_user (employees / admins)
    sys_user = session.exec(
        select(SystemUser).where(SystemUser.email == payload.email)
    ).first()

    if sys_user and verify_password(payload.password, sys_user.password_hash):
        if not sys_user.is_active:
            raise HTTPException(status_code=403, detail="Cuenta desactivada")

        role = sys_user.role.role_name.lower() if sys_user.role else "employee"
        user_id = sys_user.system_user_id
        name = sys_user.full_name
        email = sys_user.email

    else:
        # 2. Try customer
        customer = session.exec(
            select(Customer).where(Customer.email == payload.email)
        ).first()

        if not customer or not customer.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )
        if not verify_password(payload.password, customer.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )
        if not customer.is_registered:
            raise HTTPException(status_code=403, detail="Cuenta no registrada")

        role = "client"
        user_id = customer.customer_id
        name = customer.full_name
        email = customer.email

    access_token = create_access_token(user_id=user_id, role=role)
    refresh_token = create_refresh_token(user_id=user_id, role=role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_response(id=user_id, name=name, email=email, role=role),
    )
