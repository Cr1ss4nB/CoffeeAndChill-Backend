from fastapi.testclient import TestClient
from sqlmodel import Session, select
from tests.conftest import get_admin_headers
from app.models.catalog import Category, Product
from app.models.inventory import InventoryMovement


def test_get_inventory_empty(client: TestClient, test_data):
    headers = get_admin_headers(client)
    response = client.get("/api/v1/admin/inventory", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["low_stock_count"] == 0


def test_get_inventory_with_data(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)

    # Seed category
    cat = Category(category_name="Cafetería", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    # Seed products
    p1 = Product(
        name="Espresso",
        category_id=cat.category_id,
        price=50.0,
        stock_quantity=5,  # Low stock
        fulfillment_type="STOCK",
    )
    p2 = Product(
        name="Capuccino",
        category_id=cat.category_id,
        price=70.0,
        stock_quantity=20,  # OK stock
        fulfillment_type="STOCK",
    )
    session.add(p1)
    session.add(p2)
    session.commit()

    response = client.get("/api/v1/admin/inventory", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["low_stock_count"] == 1  # Espresso (5 < 10 threshold)

    # Filter by category
    response_filtered = client.get(
        f"/api/v1/admin/inventory?category_id={cat.category_id}", headers=headers
    )
    assert response_filtered.status_code == 200
    assert response_filtered.json()["total"] == 2


def test_inventory_adjustment_success(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)

    cat = Category(category_name="Cafetería", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    prod = Product(
        name="Latte",
        category_id=cat.category_id,
        price=80.0,
        stock_quantity=0,
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # positive adjustment
    payload_in = {
        "product_id": prod.product_id,
        "quantity": 15,
        "reason": "RECEIPT",
        "notes": "Llegada de lote",
    }
    resp_in = client.post("/api/v1/admin/inventory/adjustments", headers=headers, json=payload_in)
    assert resp_in.status_code == 200
    assert resp_in.json()["new_stock"] == 15

    # negative adjustment
    payload_out = {
        "product_id": prod.product_id,
        "quantity": -5,
        "reason": "WASTE",
        "notes": "Vencido",
    }
    resp_out = client.post("/api/v1/admin/inventory/adjustments", headers=headers, json=payload_out)
    assert resp_out.status_code == 200
    assert resp_out.json()["new_stock"] == 10

    # negative adjustment insufficient stock
    payload_insufficient = {
        "product_id": prod.product_id,
        "quantity": -20,
        "reason": "LOSS",
    }
    resp_err = client.post(
        "/api/v1/admin/inventory/adjustments", headers=headers, json=payload_insufficient
    )
    assert resp_err.status_code == 400
    assert "No hay suficiente stock" in resp_err.json()["detail"]

    # invalid product
    payload_nf = {
        "product_id": 9999,
        "quantity": 10,
        "reason": "RECEIPT",
    }
    resp_nf = client.post("/api/v1/admin/inventory/adjustments", headers=headers, json=payload_nf)
    assert resp_nf.status_code == 404


def test_get_inventory_movements(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)

    cat = Category(category_name="Bebidas", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    prod = Product(
        name="Agua",
        category_id=cat.category_id,
        price=30.0,
        stock_quantity=0,
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # Create a movement
    payload = {
        "product_id": prod.product_id,
        "quantity": 50,
        "reason": "RECEIPT",
        "notes": "Seed",
    }
    client.post("/api/v1/admin/inventory/adjustments", headers=headers, json=payload)

    # Get movements
    resp_move = client.get("/api/v1/admin/inventory/movements", headers=headers)
    assert resp_move.status_code == 200
    data = resp_move.json()
    assert data["total"] == 1
    assert data["items"][0]["product_name"] == "Agua"
    assert data["items"][0]["quantity"] == 50
