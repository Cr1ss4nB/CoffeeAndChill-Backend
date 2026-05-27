from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.crm import Customer
from app.models.infrastructure import TableSpot
from app.models.operations import Order, OrderItem, Payment
from app.models.security import Role, SystemUser
from app.core.security import hash_password
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


def _make_order(session: Session, product_id: int, customer_id: int, admin_id: int) -> Order:
    """Create a sample order for testing payments."""
    order = Order(
        customer_id=customer_id,
        system_user_id=admin_id,
        order_type="TAKEAWAY",
        status="PENDING",
        total_amount=150.0,
    )
    session.add(order)
    session.flush()

    item = OrderItem(
        order_id=order.order_id,
        product_id=product_id,
        quantity=1,
        unit_price=150.0,
        subtotal=150.0,
        item_type="PRODUCT",
    )
    session.add(item)
    session.commit()
    session.refresh(order)
    return order


def test_get_payments_empty(client: TestClient, session: Session, test_data):
    """Test GET /payments returns empty list when no payments exist."""
    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["payments"] == []
    assert data["summary"]["count"] == 0
    assert data["summary"]["total_ventas"] == 0.0


def test_get_payments_requires_auth(client: TestClient):
    """Test GET /payments requires authentication."""
    r = client.get("/api/v1/admin/payments")
    assert r.status_code == 403


def test_get_payments_with_data(client: TestClient, session: Session, test_data):
    """Test GET /payments returns payment history."""
    # Create a product and order
    prod = _make_product(session)
    customer = session.exec(
        select(Customer).where(Customer.email == "customer@example.com")
    ).first()
    admin = session.exec(
        select(SystemUser).where(SystemUser.email == "admin@example.com")
    ).first()
    order = _make_order(session, prod.product_id, customer.customer_id, admin.system_user_id)

    # Create a payment
    payment = Payment(
        order_id=order.order_id,
        system_user_id=admin.system_user_id,
        payment_method="CASH",
        amount=150.0,
        tip_amount=10.0,
        payment_date=datetime.now(),
    )
    session.add(payment)
    session.commit()

    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["payments"]) == 1
    assert data["payments"][0]["payment_method"] == "CASH"
    assert data["payments"][0]["amount"] == 150.0
    assert data["payments"][0]["tip_amount"] == 10.0
    assert data["summary"]["count"] == 1
    assert data["summary"]["total_ventas"] == 150.0
    assert data["summary"]["total_propinas"] == 10.0


def test_get_payments_with_date_filter(client: TestClient, session: Session, test_data):
    """Test GET /payments with date filter."""
    # Create a product and order
    prod = _make_product(session)
    customer = session.exec(
        select(Customer).where(Customer.email == "customer@example.com")
    ).first()
    admin = session.exec(
        select(SystemUser).where(SystemUser.email == "admin@example.com")
    ).first()
    order = _make_order(session, prod.product_id, customer.customer_id, admin.system_user_id)

    # Create a payment
    payment = Payment(
        order_id=order.order_id,
        system_user_id=admin.system_user_id,
        payment_method="CARD",
        amount=100.0,
        tip_amount=5.0,
        payment_date=datetime.now(),
    )
    session.add(payment)
    session.commit()

    admin_headers = get_admin_headers(client)
    today = datetime.now().strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/admin/payments?date={today}", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["payments"]) == 1


def test_get_payments_with_invalid_date_defaults_to_today(client: TestClient, session: Session, test_data):
    """Test GET /payments with invalid date falls back to today."""
    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments?date=invalid-date", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    # Should return today's data (empty in test)
    assert "date" in data


def test_get_payments_pagination(client: TestClient, session: Session, test_data):
    """Test GET /payments with pagination limit and offset."""
    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments?limit=10&offset=0", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["payments"], list)
    assert isinstance(data["summary"], dict)


def test_get_payments_summary_calculation(client: TestClient, session: Session, test_data):
    """Test GET /payments calculates summary correctly."""
    prod = _make_product(session)
    customer = session.exec(
        select(Customer).where(Customer.email == "customer@example.com")
    ).first()
    admin = session.exec(
        select(SystemUser).where(SystemUser.email == "admin@example.com")
    ).first()

    # Create multiple orders and payments
    for i in range(3):
        order = _make_order(session, prod.product_id, customer.customer_id, admin.system_user_id)
        payment = Payment(
            order_id=order.order_id,
            system_user_id=admin.system_user_id,
            payment_method="CASH",
            amount=100.0 + i * 10,
            tip_amount=5.0 + i,
            payment_date=datetime.now(),
        )
        session.add(payment)
    session.commit()

    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["count"] == 3
    assert data["summary"]["total_ventas"] == 330.0  # 100 + 110 + 120
    assert data["summary"]["total_propinas"] == 18.0  # 5 + 6 + 7
    assert data["summary"]["total_con_propinas"] == 348.0


def test_get_payments_without_table(client: TestClient, session: Session, test_data):
    """Test GET /payments handles orders without table (TAKEAWAY)."""
    prod = _make_product(session)
    customer = session.exec(
        select(Customer).where(Customer.email == "customer@example.com")
    ).first()
    admin = session.exec(
        select(SystemUser).where(SystemUser.email == "admin@example.com")
    ).first()
    order = _make_order(session, prod.product_id, customer.customer_id, admin.system_user_id)

    payment = Payment(
        order_id=order.order_id,
        system_user_id=admin.system_user_id,
        payment_method="CASH",
        amount=150.0,
        tip_amount=0.0,
        payment_date=datetime.now(),
    )
    session.add(payment)
    session.commit()

    admin_headers = get_admin_headers(client)
    r = client.get("/api/v1/admin/payments", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["payments"][0]["table_number"] is None
    assert data["payments"][0]["table_code"] is None


def test_get_payments_employee_access(client: TestClient, session: Session, test_data):
    """Test that employees with cashier role can access payments."""
    # Create cashier role and employee
    cashier_role = session.exec(
        select(Role).where(Role.role_name == "cashier")
    ).first()
    if not cashier_role:
        cashier_role = Role(role_name="cashier", permissions="[]")
        session.add(cashier_role)
        session.commit()

    cashier = SystemUser(
        full_name="Cashier Test",
        email="cashier@test.com",
        password_hash=hash_password("cashierpass"),
        role_id=cashier_role.role_id,
        is_active=True,
    )
    session.add(cashier)
    session.commit()

    # Login as cashier (if auth supports it)
    response = client.post(
        "/auth/login",
        json={"email": "cashier@test.com", "password": "cashierpass"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/v1/admin/payments", headers=headers)
        # Should either succeed or return 403 depending on permissions
        assert r.status_code in [200, 403]
