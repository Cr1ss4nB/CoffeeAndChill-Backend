from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.security import Role, SystemUser


def _admin_token(client: TestClient) -> str:
    r = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _create_employee(session: Session, email: str = "new@example.com") -> SystemUser:
    role = session.exec(select(Role).where(Role.role_name == "waiter")).first()
    if not role:
        role = Role(role_name="waiter")
        session.add(role)
        session.commit()
        session.refresh(role)
    employee = SystemUser(
        full_name="New Employee",
        email=email,
        password_hash=hash_password("secret123"),
        role_id=role.role_id,
        is_active=True,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def test_create_employee_success(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    payload = {
        "full_name": "Empleado Test",
        "email": "empleado@test.com",
        "password": "test1234",
        "role": "waiter",
        "phone": "555-1234",
    }

    r = client.post(
        "/admin/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "waiter"
    assert data["is_active"] is True


def test_create_employee_invalid_role_returns_400(client: TestClient, test_data):
    token = _admin_token(client)
    payload = {
        "full_name": "Empleado Malo",
        "email": "badrole@test.com",
        "password": "test1234",
        "role": "chef",
        "phone": "555-4321",
    }

    r = client.post(
        "/admin/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r.status_code == 400
    assert "Rol inválido" in r.json()["detail"]


def test_create_employee_duplicate_email_returns_409(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    _create_employee(session, email="existing@example.com")

    payload = {
        "full_name": "Empleado Duplicado",
        "email": "existing@example.com",
        "password": "test1234",
        "role": "waiter",
    }

    r = client.post(
        "/admin/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r.status_code == 409
    assert "correo electrónico ya está registrado" in r.json()["detail"]


def test_update_employee_role_not_found_returns_404(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    employee = _create_employee(session, email="updaterole@test.com")

    r = client.put(
        f"/admin/employees/{employee.system_user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "manager"},
    )
    assert r.status_code == 404
    assert "Rol no encontrado" in r.json()["detail"]


def test_update_employee_status_self_deactivate_returns_400(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()

    r = client.patch(
        f"/admin/employees/{admin.system_user_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert r.status_code == 400
    assert "No puedes desactivar tu propia cuenta" in r.json()["detail"]


def test_update_employee_status_deactivates_other_employee(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    employee = _create_employee(session, email="other@test.com")

    r = client.patch(
        f"/admin/employees/{employee.system_user_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_list_employees_includes_admin(client: TestClient, test_data):
    token = _admin_token(client)

    r = client.get(
        "/admin/employees",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    emails = [e["email"] for e in r.json()]
    assert "admin@example.com" in emails
