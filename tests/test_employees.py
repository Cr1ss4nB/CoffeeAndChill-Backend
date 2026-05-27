from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.security import Role, SystemUser
from tests.conftest import get_admin_headers


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
    admin_headers = get_admin_headers(client)
    payload = {
        "full_name": "Empleado Test",
        "email": "empleado@test.com",
        "password": "test1234",
        "role": "waiter",
        "phone": "555-1234",
    }

    r = client.post(
        "/api/v1/admin/employees",
        headers=admin_headers,
        json=payload,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "waiter"
    assert data["is_active"] is True


def test_create_employee_invalid_role_returns_400(client: TestClient, test_data):
    admin_headers = get_admin_headers(client)
    payload = {
        "full_name": "Empleado Malo",
        "email": "badrole@test.com",
        "password": "test1234",
        "role": "chef",
        "phone": "555-4321",
    }

    r = client.post(
        "/api/v1/admin/employees",
        headers=admin_headers,
        json=payload,
    )
    assert r.status_code == 400
    assert "Rol inválido" in r.json()["detail"]


def test_create_employee_duplicate_email_returns_409(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    _create_employee(session, email="existing@example.com")

    payload = {
        "full_name": "Empleado Duplicado",
        "email": "existing@example.com",
        "password": "test1234",
        "role": "waiter",
    }

    r = client.post(
        "/api/v1/admin/employees",
        headers=admin_headers,
        json=payload,
    )
    assert r.status_code == 409
    assert "correo electrónico ya está registrado" in r.json()["detail"]


def test_update_employee_role_not_found_returns_404(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    employee = _create_employee(session, email="updaterole@test.com")

    r = client.put(
        f"/api/v1/admin/employees/{employee.system_user_id}",
        headers=admin_headers,
        json={"role": "manager"},
    )
    assert r.status_code == 404
    assert "Rol no encontrado" in r.json()["detail"]


def test_update_employee_status_self_deactivate_returns_400(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()

    r = client.patch(
        f"/api/v1/admin/employees/{admin.system_user_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert r.status_code == 400
    assert "No puedes desactivar tu propia cuenta" in r.json()["detail"]


def test_update_employee_status_deactivates_other_employee(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    employee = _create_employee(session, email="other@test.com")

    r = client.patch(
        f"/api/v1/admin/employees/{employee.system_user_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_list_employees_includes_admin(client: TestClient, test_data):
    admin_headers = get_admin_headers(client)

    r = client.get(
        "/api/v1/admin/employees",
        headers=admin_headers,
    )
    assert r.status_code == 200
    emails = [e["email"] for e in r.json()]
    assert "admin@example.com" in emails


def test_get_employees_requires_auth(client: TestClient):
    """Test GET /employees requires authentication."""
    r = client.get("/api/v1/admin/employees")
    assert r.status_code == 403


def test_create_employee_requires_auth(client: TestClient):
    """Test POST /employees requires authentication."""
    payload = {
        "full_name": "Test Employee",
        "email": "test@test.com",
        "password": "test1234",
        "role": "waiter",
    }
    r = client.post("/api/v1/admin/employees", json=payload)
    assert r.status_code == 403


def test_update_employee_requires_auth(client: TestClient, session: Session, test_data):
    """Test PATCH /employees requires authentication."""
    employee = _create_employee(session, email="test@test.com")
    r = client.patch(
        f"/api/v1/admin/employees/{employee.system_user_id}/status",
        json={"is_active": False}
    )
    assert r.status_code == 403


def test_update_employee_full_info(client: TestClient, session: Session, test_data):
    """Test updating employee full name, email, and phone."""
    admin_headers = get_admin_headers(client)
    employee = _create_employee(session, email="oldname@test.com")

    r = client.put(
        f"/api/v1/admin/employees/{employee.system_user_id}",
        headers=admin_headers,
        json={
            "full_name": "Updated Name",
            "email": "newemail@test.com",
            "phone": "555-9999"
        }
    )
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == "newemail@test.com"
    assert data["phone"] == "555-9999"


def test_update_employee_not_found_returns_404(client: TestClient, test_data):
    """Test updating non-existent employee returns 404."""
    admin_headers = get_admin_headers(client)
    r = client.put(
        "/api/v1/admin/employees/9999",
        headers=admin_headers,
        json={"full_name": "Updated"}
    )
    assert r.status_code == 404
    assert "Empleado no encontrado" in r.json()["detail"]


def test_create_employee_with_cashier_role(client: TestClient, session: Session, test_data):
    """Test creating employee with cashier role."""
    admin_headers = get_admin_headers(client)
    payload = {
        "full_name": "Cashier Test",
        "email": "cashier@test.com",
        "password": "test1234",
        "role": "cashier",
        "phone": "555-5555",
    }

    r = client.post(
        "/api/v1/admin/employees",
        headers=admin_headers,
        json=payload,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "cashier@test.com"
    assert data["role"] == "cashier"


def test_create_employee_with_admin_role(client: TestClient, session: Session, test_data):
    """Test creating employee with admin role."""
    admin_headers = get_admin_headers(client)
    payload = {
        "full_name": "Admin Employee",
        "email": "admin_emp@test.com",
        "password": "test1234",
        "role": "admin",
        "phone": "555-6666",
    }

    r = client.post(
        "/api/v1/admin/employees",
        headers=admin_headers,
        json=payload,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "admin_emp@test.com"
    assert data["role"] == "admin"


def test_reactivate_deactivated_employee(client: TestClient, session: Session, test_data):
    """Test reactivating a previously deactivated employee."""
    admin_headers = get_admin_headers(client)
    employee = _create_employee(session, email="reactive@test.com")

    # Deactivate
    r1 = client.patch(
        f"/api/v1/admin/employees/{employee.system_user_id}/status",
        headers=admin_headers,
        json={"is_active": False}
    )
    assert r1.status_code == 200
    assert r1.json()["is_active"] is False

    # Reactivate
    r2 = client.patch(
        f"/api/v1/admin/employees/{employee.system_user_id}/status",
        headers=admin_headers,
        json={"is_active": True}
    )
    assert r2.status_code == 200
    assert r2.json()["is_active"] is True
