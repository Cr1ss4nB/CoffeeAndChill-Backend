"""Integration tests for app/routers/products.py."""
import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product


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
def existing_product(session: Session, category: Category, test_data) -> Product:
    prod = Product(
        name="Espresso",
        category_id=category.category_id,
        price=150.0,
        stock_quantity=10,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod


# ---------------------------------------------------------------------------
# POST /products
# ---------------------------------------------------------------------------

def test_create_product_success(client: TestClient, admin_headers: dict, category: Category, test_data):
    r = client.post("/products", headers=admin_headers, json={
        "name": "Cappuccino",
        "category_id": category.category_id,
        "price": 120.0,
        "stock_quantity": 5,
        "fulfillment_type": "STOCK",
    })
    assert r.status_code == 201
    data = r.json()
    for field in ("product_id", "name", "price", "stock_quantity", "status", "fulfillment_type"):
        assert field in data
    assert data["name"] == "Cappuccino"


def test_create_product_price_zero_returns_400(client: TestClient, admin_headers: dict, category: Category, test_data):
    r = client.post("/products", headers=admin_headers, json={
        "name": "Bad",
        "category_id": category.category_id,
        "price": 0,
        "stock_quantity": 5,
        "fulfillment_type": "STOCK",
    })
    assert r.status_code == 400


def test_create_product_negative_stock_returns_400(client: TestClient, admin_headers: dict, category: Category, test_data):
    r = client.post("/products", headers=admin_headers, json={
        "name": "Bad",
        "category_id": category.category_id,
        "price": 100.0,
        "stock_quantity": -1,
        "fulfillment_type": "STOCK",
    })
    assert r.status_code == 400


def test_create_product_invalid_category_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.post("/products", headers=admin_headers, json={
        "name": "Bad",
        "category_id": 99999,
        "price": 100.0,
        "stock_quantity": 5,
        "fulfillment_type": "STOCK",
    })
    assert r.status_code == 404


def test_create_product_invalid_fulfillment_returns_400(client: TestClient, admin_headers: dict, category: Category, test_data):
    r = client.post("/products", headers=admin_headers, json={
        "name": "Bad",
        "category_id": category.category_id,
        "price": 100.0,
        "stock_quantity": 5,
        "fulfillment_type": "INVALID",
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /products/{id}
# ---------------------------------------------------------------------------

def test_patch_product_success(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}", headers=admin_headers, json={
        "name": "Espresso Updated",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Espresso Updated"
    for field in ("product_id", "name", "price", "stock_quantity", "status", "fulfillment_type"):
        assert field in data


def test_patch_product_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.patch("/products/99999", headers=admin_headers, json={"name": "X"})
    assert r.status_code == 404


def test_patch_product_invalid_price_returns_400(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}", headers=admin_headers, json={"price": -5.0})
    assert r.status_code == 400


def test_patch_product_invalid_category_returns_404(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}", headers=admin_headers, json={"category_id": 99999})
    assert r.status_code == 404


def test_patch_product_invalid_fulfillment_returns_400(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}", headers=admin_headers, json={"fulfillment_type": "WRONG"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /products/{id}/status
# ---------------------------------------------------------------------------

def test_patch_product_status_inactive(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}/status", headers=admin_headers, json={"status": "INACTIVE"})
    assert r.status_code == 200
    assert r.json()["status"] == "INACTIVE"


def test_patch_product_status_active(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}/status", headers=admin_headers, json={"status": "ACTIVE"})
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"


def test_patch_product_status_invalid_returns_400(client: TestClient, admin_headers: dict, existing_product: Product, test_data):
    r = client.patch(f"/products/{existing_product.product_id}/status", headers=admin_headers, json={"status": "DELETED"})
    assert r.status_code == 400


def test_patch_product_status_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.patch("/products/99999/status", headers=admin_headers, json={"status": "ACTIVE"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /products/upload-image
# ---------------------------------------------------------------------------

def test_upload_image_valid_jpeg(client: TestClient, admin_headers: dict, test_data):
    with patch("app.routers.products.os.makedirs"), patch("builtins.open", MagicMock()):
        r = client.post(
            "/products/upload-image",
            headers=admin_headers,
            files={"file": ("photo.jpg", io.BytesIO(b"fake-image-data"), "image/jpeg")},
        )
    assert r.status_code == 200
    assert "image_url" in r.json()
    assert r.json()["image_url"]


def test_upload_image_invalid_mime_returns_400(client: TestClient, admin_headers: dict, test_data):
    r = client.post(
        "/products/upload-image",
        headers=admin_headers,
        files={"file": ("doc.pdf", io.BytesIO(b"data"), "application/pdf")},
    )
    assert r.status_code == 400


def test_upload_image_too_large_returns_400(client: TestClient, admin_headers: dict, test_data):
    big_data = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
    r = client.post(
        "/products/upload-image",
        headers=admin_headers,
        files={"file": ("big.jpg", io.BytesIO(big_data), "image/jpeg")},
    )
    assert r.status_code == 400
