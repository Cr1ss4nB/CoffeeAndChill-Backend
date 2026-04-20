from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.catalog import Product


def test_checkout_success(client: TestClient, session: Session, test_data):
    # 1. Login
    login_resp = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "customerpass"}
    )
    token = login_resp.json()["access_token"]

    # 2. Add product explicitly
    prod = Product(name="Test Espresso", category_id=1, price=150.0, stock_quantity=10, status="ACTIVE")
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # 3. Request Checkout
    payload = {
        "order_type": "TAKEAWAY",
        "items": [
            {
                "product_id": prod.product_id,
                "quantity": 2
            }
        ]
    }

    response = client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert data["order_type"] == "TAKEAWAY"
    assert data["status"] == "PENDING"
    assert data["total_amount"] == 300.0

    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["subtotal"] == 300.0

    # Verify stock reduction
    session.refresh(prod)
    assert prod.stock_quantity == 8


def test_checkout_insufficient_stock(client: TestClient, session: Session, test_data):
    login_resp = client.post("/auth/login", json={"email": "customer@example.com", "password": "customerpass"})
    token = login_resp.json()["access_token"]

    prod = Product(name="No Stock", category_id=1, price=100.0, stock_quantity=1, status="ACTIVE")
    session.add(prod)
    session.commit()
    session.refresh(prod)

    payload = {
        "order_type": "DINE_IN",
        "items": [{"product_id": prod.product_id, "quantity": 5}]
    }

    response = client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )

    assert response.status_code == 400
    assert "Stock insuficiente" in response.json()["detail"]


def test_checkout_unauthorized(client: TestClient):
    response = client.post(
        "/orders/checkout",
        json={"order_type": "DELIVERY", "items": [{"product_id": 1, "quantity": 1}]}
    )
    assert response.status_code == 403
