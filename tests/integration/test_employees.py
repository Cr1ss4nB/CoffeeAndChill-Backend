"""Integration tests for app/routers/employees.py."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.security import Role, SystemUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(client: TestClient, test_data) -> dict:
    token = _login(client, "admin@example.com", "adminpass")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_employee(session: Session, test_data) -> SystemUser:
    """Creates a second active employee (waiter) for update/status tests."""
    role = session.exec(select(Role).where(Role.role_name == "waiter")).first()
    if not role:
        role = Role(role_name="waiter", permissions="[]")
        session.add(role)
        session.commit()
        session.refresh(role)
    emp = SystemUser(
        full_name="Juan Waiter",
        email="waiter@cafe.com",
        password_hash=hash_password("waiterpass"),
        role_id=role.role_id,
        is_active=True,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)
    return emp


# ---------------------------------------------------------------------------
# GET /admin/employees
# ---------------------------------------------------------------------------

def test_get_employees_returns_200_list(client: TestClient, admin_headers: dict, test_data):
    r = client.get("/api/v1/admin/employees", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check required fields
    for emp in data:
        for field in ("employee_id", "full_name", "email", "role", "is_active"):
            assert field in emp


def test_get_employees_no_token_returns_403(client: TestClient, test_data):
    r = client.get("/api/v1/admin/employees")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/employees
# ---------------------------------------------------------------------------

def test_create_employee_success(client: TestClient, admin_headers: dict, test_data):
    r = client.post("/api/v1/admin/employees", headers=admin_headers, json={
        "full_name": "Maria Cashier",
        "email": "maria@cafe.com",
        "password": "pass1234",
        "role": "cashier",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "maria@cafe.com"
    assert data["role"] == "cashier"
    assert data["is_active"] is True


def test_create_employee_duplicate_email_returns_409(client: TestClient, admin_headers: dict, test_data):
    r = client.post("/api/v1/admin/employees", headers=admin_headers, json={
        "full_name": "Dup",
        "email": "admin@example.com",
        "password": "pass",
        "role": "waiter",
    })
    assert r.status_code == 409


def test_create_employee_invalid_role_returns_400(client: TestClient, admin_headers: dict, test_data):
    r = client.post("/api/v1/admin/employees", headers=admin_headers, json={
        "full_name": "Bad Role",
        "email": "badrole@cafe.com",
        "password": "pass",
        "role": "superuser",
    })
    assert r.status_code == 400


def test_create_employee_no_token_returns_403(client: TestClient, test_data):
    r = client.post("/api/v1/admin/employees", json={
        "full_name": "X",
        "email": "x@cafe.com",
        "password": "p",
        "role": "waiter",
    })
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# PUT /admin/employees/{id}
# ---------------------------------------------------------------------------

def test_update_employee_success(client: TestClient, admin_headers: dict, second_employee: SystemUser, test_data):
    r = client.put(f"/api/v1/admin/employees/{second_employee.system_user_id}", headers=admin_headers, json={
        "full_name": "Juan Updated",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "Juan Updated"
    assert data["employee_id"] == second_employee.system_user_id


def test_update_employee_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.put("/api/v1/admin/employees/99999", headers=admin_headers, json={"full_name": "X"})
    assert r.status_code == 404


def test_update_employee_duplicate_email_returns_409(client: TestClient, admin_headers: dict, second_employee: SystemUser, test_data):
    r = client.put(f"/api/v1/admin/employees/{second_employee.system_user_id}", headers=admin_headers, json={
        "email": "admin@example.com",
    })
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /admin/employees/{id}/status
# ---------------------------------------------------------------------------

def test_patch_employee_status_success(client: TestClient, admin_headers: dict, second_employee: SystemUser, test_data):
    r = client.patch(f"/api/v1/admin/employees/{second_employee.system_user_id}/status", headers=admin_headers, json={
        "is_active": False,
    })
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_patch_employee_status_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.patch("/api/v1/admin/employees/99999/status", headers=admin_headers, json={"is_active": False})
    assert r.status_code == 404


def test_patch_employee_status_self_returns_400(client: TestClient, session: Session, admin_headers: dict, test_data):
    """Admin cannot change their own status."""
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    r = client.patch(f"/api/v1/admin/employees/{admin.system_user_id}/status", headers=admin_headers, json={
        "is_active": False,
    })
    assert r.status_code == 400
