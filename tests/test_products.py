"""
P0 — Tests para POST/PATCH /products y PATCH /products/{id}/status.
Cubre: creación válida/inválida, actualización, toggle de estado,
guards de autenticación, y regresión de visibilidad en catálogo.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product

@pytest.fixture
def admin_token(client: TestClient, test_data) -> str:
    r = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def _make_category(session: Session, name: str = "Bebidas") -> Category:
    cat = Category(category_name=name, type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat

def _make_product(
    session: Session,
    category_id: int,
    name: str = "Espresso",
    price: float = 3500.0,
    stock: int = 10,
    status: str = "ACTIVE",
    fulfillment: str = "STOCK",
) -> Product:
    p = Product(
        name=name,
        category_id=category_id,
        price=price,
        stock_quantity=stock,
        status=status,
        fulfillment_type=fulfillment,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

def test_create_product_stock(client: TestClient, session: Session, admin_token: str):
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={
            "name": "Americano",
            "category_id": cat.category_id,
            "price": 3500.0,
            "stock_quantity": 20,
            "fulfillment_type": "STOCK",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Americano"
    assert data["fulfillment_type"] == "STOCK"
    assert data["available_to_sell"] == 20
    assert "product_id" in data

def test_create_product_ingredients_fulfillment(
    client: TestClient, session: Session, admin_token: str
):
    """Producto tipo INGREDIENTS sin receta: available_to_sell cae back a STOCK (0)."""
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={
            "name": "Café con leche",
            "category_id": cat.category_id,
            "price": 4000.0,
            "stock_quantity": 0,
            "fulfillment_type": "INGREDIENTS",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["fulfillment_type"] == "INGREDIENTS"
    assert data["available_to_sell"] == 0

def test_create_product_rejects_price_zero(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={"name": "X", "category_id": cat.category_id, "price": 0, "stock_quantity": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "precio" in r.json()["detail"].lower()

def test_create_product_rejects_negative_price(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={"name": "X", "category_id": cat.category_id, "price": -100.0, "stock_quantity": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400

def test_create_product_rejects_negative_stock(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={"name": "X", "category_id": cat.category_id, "price": 1000.0, "stock_quantity": -1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "stock" in r.json()["detail"].lower()

def test_create_product_rejects_unknown_category(
    client: TestClient, session: Session, admin_token: str
):
    r = client.post(
        "/products",
        json={"name": "X", "category_id": 99999, "price": 1000.0, "stock_quantity": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_create_product_rejects_invalid_fulfillment_type(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    r = client.post(
        "/products",
        json={
            "name": "X",
            "category_id": cat.category_id,
            "price": 1000.0,
            "stock_quantity": 5,
            "fulfillment_type": "MAGIC",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_create_product_requires_auth(client: TestClient, session: Session):
    r = client.post(
        "/products",
        json={"name": "X", "category_id": 1, "price": 1000.0, "stock_quantity": 5},
    )
    assert r.status_code in (401, 403)

def test_update_product_name_and_price(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, name="Viejo", price=1000.0)

    r = client.patch(
        f"/products/{p.product_id}",
        json={"name": "Nuevo", "price": 2500.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Nuevo"
    assert data["price"] == 2500.0


def test_update_product_not_found(client: TestClient, session: Session, admin_token: str):
    r = client.patch(
        "/products/99999",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_update_product_rejects_invalid_price(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id)

    r = client.patch(
        f"/products/{p.product_id}",
        json={"price": -50.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_update_product_fulfillment_type(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, fulfillment="STOCK")

    r = client.patch(
        f"/products/{p.product_id}",
        json={"fulfillment_type": "INGREDIENTS"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["fulfillment_type"] == "INGREDIENTS"


def test_update_product_requires_auth(client: TestClient, session: Session):
    r = client.patch("/products/1", json={"name": "X"})
    assert r.status_code in (401, 403)

def test_toggle_active_to_inactive_hides_from_catalog(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, status="ACTIVE")

    r = client.patch(
        f"/products/{p.product_id}/status",
        json={"status": "INACTIVE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "INACTIVE"

    # Producto NO debe aparecer en catálogo con active_only=true (default)
    catalog_r = client.get("/catalog/products")
    assert catalog_r.status_code == 200
    ids = [prod["product_id"] for prod in catalog_r.json()]
    assert p.product_id not in ids


def test_toggle_inactive_to_active_reappears_in_catalog(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, status="INACTIVE")

    # No debe aparecer antes
    catalog_r = client.get("/catalog/products")
    assert p.product_id not in [prod["product_id"] for prod in catalog_r.json()]

    r = client.patch(
        f"/products/{p.product_id}/status",
        json={"status": "ACTIVE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"

    # Ahora sí debe aparecer
    catalog_r = client.get("/catalog/products")
    ids = [prod["product_id"] for prod in catalog_r.json()]
    assert p.product_id in ids


def test_toggle_status_invalid_value(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id)

    r = client.patch(
        f"/products/{p.product_id}/status",
        json={"status": "SUSPENDED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400


def test_toggle_status_not_found(client: TestClient, session: Session, admin_token: str):
    r = client.patch(
        "/products/99999/status",
        json={"status": "INACTIVE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404


def test_toggle_status_requires_auth(client: TestClient):
    r = client.patch("/products/1/status", json={"status": "INACTIVE"})
    assert r.status_code in (401, 403)
