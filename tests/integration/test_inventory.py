"""Integration tests for app/routers/inventory.py."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.inventory import InventoryMovement
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


@pytest.fixture
def category(session: Session, test_data) -> Category:
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def product_with_stock(session: Session, category: Category, test_data) -> Product:
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    prod = Product(
        name="Espresso",
        category_id=category.category_id,
        price=150.0,
        stock_quantity=50,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    # Add an IN movement so stock is tracked
    session.add(InventoryMovement(
        product_id=prod.product_id,
        system_user_id=admin.system_user_id,
        movement_type="IN",
        quantity=50,
        reason="RECEIPT",
    ))
    session.commit()
    return prod


@pytest.fixture
def low_stock_product(session: Session, category: Category, test_data) -> Product:
    """Product with stock below LOW_STOCK_THRESHOLD (default 5)."""
    prod = Product(
        name="Agua",
        category_id=category.category_id,
        price=20.0,
        stock_quantity=1,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod


# ---------------------------------------------------------------------------
# GET /inventory
# ---------------------------------------------------------------------------

def test_get_inventory_pagination(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.get("/api/v1/admin/inventory?page=1&limit=5", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) <= 5
    assert "low_stock_count" in data


def test_get_inventory_page_beyond_last_returns_empty(client: TestClient, admin_headers: dict, test_data):
    r = client.get("/api/v1/admin/inventory?page=9999&limit=10", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_get_inventory_category_filter(client: TestClient, admin_headers: dict, product_with_stock, category, test_data):
    r = client.get(f"/api/v1/admin/inventory?category_id={category.category_id}", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    for item in items:
        assert item["category"] == category.category_name


def test_get_inventory_low_stock_count(client: TestClient, admin_headers: dict, low_stock_product, test_data):
    r = client.get("/api/v1/admin/inventory", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["low_stock_count"] >= 1


# ---------------------------------------------------------------------------
# POST /inventory/adjustments
# ---------------------------------------------------------------------------

def test_inventory_adjustment_positive_in(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.post("/api/v1/admin/inventory/adjustments", headers=admin_headers, json={
        "product_id": product_with_stock.product_id,
        "quantity": 10,
        "reason": "RECEIPT",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["new_stock"] == 60


def test_inventory_adjustment_negative_out(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.post("/api/v1/admin/inventory/adjustments", headers=admin_headers, json={
        "product_id": product_with_stock.product_id,
        "quantity": -10,
        "reason": "WASTE",
    })
    assert r.status_code == 200
    assert r.json()["new_stock"] == 40


def test_inventory_adjustment_insufficient_stock_returns_400(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.post("/api/v1/admin/inventory/adjustments", headers=admin_headers, json={
        "product_id": product_with_stock.product_id,
        "quantity": -9999,
        "reason": "WASTE",
    })
    assert r.status_code == 400


def test_inventory_adjustment_product_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.post("/api/v1/admin/inventory/adjustments", headers=admin_headers, json={
        "product_id": 99999,
        "quantity": 10,
        "reason": "RECEIPT",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /inventory/movements
# ---------------------------------------------------------------------------

def test_get_movements_no_filter(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.get("/api/v1/admin/inventory/movements", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_get_movements_movement_type_filter(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.get("/api/v1/admin/inventory/movements?movement_type=IN", headers=admin_headers)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["movement_type"] == "IN"


def test_get_movements_product_id_filter(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.get(f"/api/v1/admin/inventory/movements?product_id={product_with_stock.product_id}", headers=admin_headers)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["product_id"] == product_with_stock.product_id


def test_get_movements_date_filter(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    from datetime import date
    today = date.today().isoformat()
    r = client.get(f"/api/v1/admin/inventory/movements?start_date={today}&end_date={today}", headers=admin_headers)
    assert r.status_code == 200
    assert "items" in r.json()


def test_get_movements_pagination(client: TestClient, admin_headers: dict, product_with_stock, test_data):
    r = client.get("/api/v1/admin/inventory/movements?page=1&limit=1", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 1
