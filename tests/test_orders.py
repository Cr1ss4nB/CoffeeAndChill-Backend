from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product
from app.models.infrastructure import TableSpot
from tests.conftest import get_admin_headers, get_customer_headers


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
    r = client.post("/api/v1/orders/checkout", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert r.status_code == 201, r.text
    return r.json()

def test_status_transition_pending_to_preparing(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    headers = get_customer_headers(client)
    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={"order_type": "TAKEAWAY", "items": [{"product_id": prod.product_id, "quantity": 1}]}
    )
    assert response.status_code == 201
    order = response.json()
    order_id = order["order_id"]

    admin_headers = get_admin_headers(client)
    r = client.patch(
        f"/api/v1/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "PREPARING"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "PREPARING"


def test_status_transition_preparing_to_ready(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    headers = get_customer_headers(client)
    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={"order_type": "TAKEAWAY", "items": [{"product_id": prod.product_id, "quantity": 1}]}
    )
    order = response.json()
    order_id = order["order_id"]
    admin_headers = get_admin_headers(client)

    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "PREPARING"})
    r = client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "READY"})
    assert r.status_code == 200
    assert r.json()["status"] == "READY"


def test_status_transition_ready_to_delivered_frees_table(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    table = _make_table(session)
    headers = get_customer_headers(client)
    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={"order_type": "DINE_IN", "items": [{"product_id": prod.product_id, "quantity": 1}], "table_id": table.table_id}
    )
    order = response.json()
    order_id = order["order_id"]
    admin_headers = get_admin_headers(client)

    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "PREPARING"})
    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "READY"})
    r = client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "DELIVERED"})

    assert r.status_code == 200
    assert r.json()["status"] == "DELIVERED"
    session.refresh(table)
    assert table.status == "FREE"


def test_status_transition_invalid_returns_400(client: TestClient, session: Session, test_data):
    prod = _make_product(session)
    headers = get_customer_headers(client)
    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={"order_type": "TAKEAWAY", "items": [{"product_id": prod.product_id, "quantity": 1}]}
    )
    order = response.json()
    order_id = order["order_id"]
    admin_headers = get_admin_headers(client)

    # Advance to DELIVERED
    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "PREPARING"})
    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "READY"})
    client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "DELIVERED"})

    # Try to go back — must fail
    r = client.patch(f"/api/v1/orders/{order_id}/status", headers=admin_headers, json={"status": "PENDING"})
    assert r.status_code == 400
    assert "DELIVERED" in r.json()["detail"]


def test_status_order_not_found(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    r = client.patch(
        "/api/v1/orders/99999/status",
        headers=admin_headers,
        json={"status": "PREPARING"},
    )
    assert r.status_code == 404

def test_order_response_includes_product_name(client: TestClient, session: Session, test_data):
    prod = _make_product(session, name="Cappuccino")
    headers = get_customer_headers(client)
    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json={"order_type": "TAKEAWAY", "items": [{"product_id": prod.product_id, "quantity": 1}]}
    )
    order = response.json()

    assert order["items"][0]["product_name"] == "Cappuccino"


def test_public_order_status_includes_product_name(client: TestClient, session: Session, test_data):
    prod = _make_product(session, name="Latte")
    table = _make_table(session, number=2)

    # Place order via public endpoint
    r = client.post(
        "/api/v1/public/orders",
        json={
            "table_code": table.table_code,
            "items": [{"product_id": prod.product_id, "quantity": 1}],
        },
    )
    assert r.status_code == 201
    order_id = r.json()["order_id"]

    # Fetch public status
    r2 = client.get(f"/api/v1/public/orders/{order_id}")
    assert r2.status_code == 200
    assert r2.json()["items"][0]["product_name"] == "Latte"

def test_orders_stream_requires_auth(client: TestClient, session: Session, test_data):
    r = client.get("/api/v1/orders/stream")
    assert r.status_code == 403


def test_orders_stream_returns_event_stream_content_type(client: TestClient, session: Session, test_data):
    admin_headers = get_admin_headers(client)
    with client.stream("GET", "/api/v1/orders/stream", headers=admin_headers) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_public_order_stream_returns_event_stream_content_type(client: TestClient, session: Session, test_data):
    with client.stream("GET", "/api/v1/public/orders/1/stream") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


def test_checkout_success(client: TestClient, session: Session, test_data):
    # 1. Add product explicitly
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    prod = Product(
        name="Test Espresso",
        category_id=cat.category_id,
        price=150.0,
        stock_quantity=10,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    headers = get_customer_headers(client)

    # 2. Request Checkout
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
        "/api/v1/orders/checkout",
        headers=headers,
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
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    prod = Product(
        name="No Stock",
        category_id=cat.category_id,
        price=100.0,
        stock_quantity=1,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    headers = get_customer_headers(client)
    payload = {
        "order_type": "DINE_IN",
        "items": [{"product_id": prod.product_id, "quantity": 5}]
    }

    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json=payload
    )

    assert response.status_code == 400
    assert "Stock insuficiente" in response.json()["detail"]


def test_checkout_unauthorized(client: TestClient):
    response = client.post(
        "/api/v1/orders/checkout",
        json={"order_type": "DELIVERY", "items": [{"product_id": 1, "quantity": 1}]}
    )
    assert response.status_code == 403


def test_checkout_without_items_returns_400(client: TestClient, session: Session, test_data):
    """Test checkout fails when items list is empty."""
    headers = get_customer_headers(client)
    payload = {
        "order_type": "TAKEAWAY",
        "items": []
    }

    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json=payload
    )
    assert response.status_code == 400


def test_checkout_product_not_found_returns_400(client: TestClient, session: Session, test_data):
    """Test checkout fails when product doesn't exist."""
    headers = get_customer_headers(client)
    payload = {
        "order_type": "TAKEAWAY",
        "items": [{"product_id": 999, "quantity": 1}]
    }

    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json=payload
    )
    assert response.status_code == 400


def test_checkout_zero_stock_product_returns_400(client: TestClient, session: Session, test_data):
    """Test checkout fails when product stock is zero."""
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    prod = Product(
        name="Out of Stock",
        category_id=cat.category_id,
        price=100.0,
        stock_quantity=0,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    headers = get_customer_headers(client)
    payload = {
        "order_type": "TAKEAWAY",
        "items": [{"product_id": prod.product_id, "quantity": 1}]
    }

    response = client.post(
        "/api/v1/orders/checkout",
        headers=headers,
        json=payload
    )
    assert response.status_code == 400
    assert "Stock insuficiente" in response.json()["detail"]
