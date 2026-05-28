"""Integration tests for app/routers/payments.py."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.infrastructure import TableSpot
from app.models.operations import Order, Payment
from app.models.security import SystemUser

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(client: TestClient, test_data) -> dict:
    token = _login(client, "admin@example.com", "adminpass")
    return {"Authorization": f"Bearer {token}"}


def _seed_payment(session: Session, admin_id: int, amount: float = 100.0, tip: float = 10.0) -> Payment:
    """Create a minimal order + payment for today."""
    order = Order(
        system_user_id=admin_id,
        order_type="TAKEAWAY",
        status="DELIVERED",
        subtotal=amount,
        total_amount=amount,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    payment = Payment(
        order_id=order.order_id,
        system_user_id=admin_id,
        payment_method="CASH",
        amount=amount,
        tip_amount=tip,
        status="COMPLETED",
        payment_date=datetime.now(timezone.utc),
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


# ---------------------------------------------------------------------------
# GET /payments
# ---------------------------------------------------------------------------

def test_payments_empty_db(client: TestClient, admin_headers: dict, test_data):
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["payments"] == []
    assert data["summary"]["count"] == 0
    assert data["summary"]["total_ventas"] == 0
    assert data["summary"]["total_propinas"] == 0
    assert data["summary"]["total_con_propinas"] == 0


def test_payments_with_data_today(client: TestClient, session: Session, admin_headers: dict, test_data):
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    _seed_payment(session, admin.system_user_id, amount=200.0, tip=20.0)
    _seed_payment(session, admin.system_user_id, amount=150.0, tip=15.0)

    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["count"] == 2
    assert data["summary"]["total_ventas"] > 0
    assert data["summary"]["total_propinas"] > 0


def test_payments_response_envelope_fields(client: TestClient, admin_headers: dict, test_data):
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "payments" in data
    assert "summary" in data
    assert "date" in data
    for field in ("count", "total_ventas", "total_propinas", "total_con_propinas"):
        assert field in data["summary"]


def test_payments_valid_date_filter(client: TestClient, session: Session, admin_headers: dict, test_data):
    from datetime import date
    today = date.today().isoformat()
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    _seed_payment(session, admin.system_user_id)

    r = client.get(f"/api/v1/admin/payments?date={today}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["date"] == today


def test_payments_invalid_date_defaults_to_today(client: TestClient, admin_headers: dict, test_data):
    from datetime import date
    r = client.get("/api/v1/admin/payments?date=not-a-date", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["date"] == date.today().isoformat()


def test_payments_pagination_limit(client: TestClient, session: Session, admin_headers: dict, test_data):
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    for _ in range(5):
        _seed_payment(session, admin.system_user_id)

    r = client.get("/api/v1/admin/payments?limit=2&offset=0", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["payments"]) <= 2


def test_payments_pagination_offset_beyond_total(client: TestClient, session: Session, admin_headers: dict, test_data):
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    _seed_payment(session, admin.system_user_id)

    r = client.get("/api/v1/admin/payments?offset=9999", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["payments"] == []
