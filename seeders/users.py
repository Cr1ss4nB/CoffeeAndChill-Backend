"""Seeder: roles, usuario de sistema (movimientos FK) y customer de prueba."""

from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.crm import Customer
from app.models.security import Role, SystemUser

# Mismo par email/contraseña que `tests/conftest.py` (pruebas de auth coherentes).
# Son datos insertados en BD: `hash_password` → bcrypt, no interviene el JWT
# (el JWT se crea al llamar a /auth/login, con SECRET_KEY de la app).
_DEMO_ADMIN_EMAIL = "admin@example.com"
_DEMO_ADMIN_PASSWORD = "adminpass"
_DEMO_CLIENT_EMAIL = "customer@example.com"
_DEMO_CLIENT_PASSWORD = "customerpass"


def seed_demo_users(session: Session) -> int:
    """
    Crea roles `admin` y `employee`, un administrador y un cliente demo.
    Idempotente: no duplica filas si el email ya existe.
    Devuelve `system_user_id` del admin (para movimientos de inventario/insumos).
    """
    role_admin = session.exec(select(Role).where(Role.role_name == "admin")).first()
    if not role_admin:
        role_admin = Role(role_name="admin")
        session.add(role_admin)
    role_employee = session.exec(select(Role).where(Role.role_name == "employee")).first()
    if not role_employee:
        role_employee = Role(role_name="employee")
        session.add(role_employee)
    session.commit()
    session.refresh(role_admin)
    session.refresh(role_employee)

    admin = session.exec(
        select(SystemUser).where(SystemUser.email == _DEMO_ADMIN_EMAIL)
    ).first()
    if not admin:
        admin = SystemUser(
            full_name="Admin Demo",
            email=_DEMO_ADMIN_EMAIL,
            password_hash=hash_password(_DEMO_ADMIN_PASSWORD),
            role_id=role_admin.role_id,
            is_active=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

    client = session.exec(
        select(Customer).where(Customer.email == _DEMO_CLIENT_EMAIL)
    ).first()
    if not client:
        client = Customer(
            full_name="Cliente Demo",
            email=_DEMO_CLIENT_EMAIL,
            password_hash=hash_password(_DEMO_CLIENT_PASSWORD),
            is_registered=True,
            loyalty_points=0,
        )
        session.add(client)
        session.commit()

    return admin.system_user_id
