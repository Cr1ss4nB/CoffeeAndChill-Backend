from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator


# ── Register (only for clients self-registering) ──────────────────────────────

class CustomerRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("full_name")
    @classmethod
    def name_min_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v.strip()


# ── Login (unified: employee/admin via system_user, client via customer) ───────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Responses ─────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str          # admin | employee | client

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
