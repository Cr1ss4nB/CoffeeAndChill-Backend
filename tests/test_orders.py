import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.catalog import Product, Category
from app.models.infrastructure import TableSpot

def _admin_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
    return r.json()["access_token"]


def _customer_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": "customer@example.com", "password": "customerpass"})
    return r.json()["access_token"]


def _make_product(session: Session, name: str = "Espresso", stock: int = 10) -> Product:
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    prod = Product(
        name=name,
        category_id=cat.category_id,
        price=150.0,
        stock_quantity=stock,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod


def _make_table(session: Session, number: int = 1) -> TableSpot:
    table = TableSpot(
        table_number=number,
        table_code=f"T{number:03d}",
        capacity=4,
        status="FREE",
        is_active=True,
    )
    session.add(table)
    session.commit()
    session.refresh(table)
    return table


def _checkout(client: TestClient, token: str, product_id: int, order_type: str = "TAKEAWAY", table_id: int | None = None) -> dict:
    payload = {
        "order_type": order_type,
        "items": [{"product_id": product_id, "quantity": 1}],
    }
    if table_id:
        payload["table_id"] = table_id
    r = client.post("/orders/checkout", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert r.status_code == 201, r.text
    return r.json()

def test_status_transition_pending_to_preparing(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    token = _customer_token(client)
    order = _checkout(client, token, prod.product_id)
    order_id = order["order_id"]

    admin_token = _admin_token(client)
    r = client.patch(
        f"/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "PREPARING"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "PREPARING"


def test_status_transition_preparing_to_ready(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    token = _customer_token(client)
    order = _checkout(client, token, prod.product_id)
    order_id = order["order_id"]
    admin_token = _admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "PREPARING"})
    r = client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "READY"})
    assert r.status_code == 200
    assert r.json()["status"] == "READY"


def test_status_transition_ready_to_delivered_frees_table(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    table = _make_table(session)
    token = _customer_token(client)
    order = _checkout(client, token, prod.product_id, order_type="DINE_IN", table_id=table.table_id)
    order_id = order["order_id"]
    admin_token = _admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "PREPARING"})
    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "READY"})
    r = client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "DELIVERED"})

    assert r.status_code == 200
    assert r.json()["status"] == "DELIVERED"
    session.refresh(table)
    assert table.status == "FREE"


def test_status_transition_invalid_returns_400(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    token = _customer_token(client)
    order = _checkout(client, token, prod.product_id)
    order_id = order["order_id"]
    admin_token = _admin_token(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Advance to DELIVERED
    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "PREPARING"})
    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "READY"})
    client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "DELIVERED"})

    # Try to go back — must fail
    r = client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "PENDING"})
    assert r.status_code == 400
    assert "DELIVERED" in r.json()["detail"]


def test_status_order_not_found(client: TestClient, session: Session, test_data):
    admin_token = _admin_token(client)
    r = client.patch(
        "/orders/99999/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "PREPARING"},
    )
    assert r.status_code == 404

def test_order_response_includes_product_name(client: TestClient, session: Session, test_data):
    prod = _make_product(session, name="Cappuccino")
    token = _customer_token(client)
    order = _checkout(client, token, prod.product_id)

    assert order["items"][0]["product_name"] == "Cappuccino"


def test_public_order_status_includes_product_name(client: TestClient, session: Session, test_data):
    prod = _make_product(session, name="Latte")
    table = _make_table(session, number=2)

    # Place order via public endpoint
    r = client.post(
        "/public/orders",
        json={
            "table_code": table.table_code,
            "items": [{"product_id": prod.product_id, "quantity": 1}],
        },
    )
    assert r.status_code == 201
    order_id = r.json()["order_id"]

    # Fetch public status
    r2 = client.get(f"/public/orders/{order_id}")
    assert r2.status_code == 200
    assert r2.json()["items"][0]["product_name"] == "Latte"

def test_orders_stream_requires_auth(client: TestClient, session: Session, test_data):
    r = client.get("/orders/stream")
    assert r.status_code == 403


def test_orders_stream_returns_event_stream_content_type(client: TestClient, session: Session, test_data):
    admin_token = _admin_token(client)
    with client.stream("GET", "/orders/stream", headers={"Authorization": f"Bearer {admin_token}"}) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_public_order_stream_returns_event_stream_content_type(client: TestClient, session: Session, test_data):
    with client.stream("GET", "/public/orders/1/stream") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_checkout_success(client: TestClient, session: Session, test_data):
    # 1. Login
    login_resp = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "customerpass"}
    )
    token = login_resp.json()["access_token"]

    # 2. Add product explicitly
    prod = Product(
        name="Test Espresso",
        category_id=1,
        price=150.0,
        stock_quantity=10,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
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

    prod = Product(
        name="No Stock",
        category_id=1,
        price=100.0,
        stock_quantity=1,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
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
