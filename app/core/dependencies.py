from datetime import datetime, timezone

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.redis import get_redis_client
from app.core.security import decode_token
from app.models.crm import Customer
from app.models.security import SystemUser
from app.schemas.auth import UserResponse

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> UserResponse:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Token malformado")

    # Check blacklist
    if redis_client.exists(f"blacklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revocado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration again (jwt.decode already does this, but sanity check)
    exp = payload.get("exp")
    if not exp or datetime.now(timezone.utc).timestamp() > exp:
        raise HTTPException(status_code=401, detail="Token expirado")

    user_id = int(payload.get("sub"))
    role = payload.get("role")

    if role == "client":
        user = session.get(Customer, user_id)
        if not user or not user.is_registered:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        name = user.full_name
        email = user.email
        is_active = True
    else:
        user = session.get(SystemUser, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Usuario inactivo o no encontrado")
        name = user.full_name
        email = user.email
        is_active = user.is_active

    return UserResponse(id=user_id, name=name, email=email, role=role, is_active=is_active)


def require_role(allowed_roles: list[str]):
    def role_checker(user: UserResponse = Depends(get_current_user)):
        if user.role not in allowed_roles and "all" not in allowed_roles:
            raise HTTPException(status_code=403, detail="No tienes permisos suficientes")
        return user
    return role_checker
