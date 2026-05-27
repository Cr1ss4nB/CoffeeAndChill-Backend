import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product
from app.models.infrastructure import TableSpot
from app.models.operations import Order, OrderItem
from app.models.security import Role, SystemUser
from app.core.security import hash_password

from sqlmodel import select

def _admin_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
    return r.json()["access_token"]

def _employee_token(client: TestClient, session: Session) -> str:
    # Get employee role
    role_emp = session.exec(select(Role).where(Role.role_name == "employee")).first()
    if not role_emp:
        role_emp = Role(role_name="employee")
        session.add(role_emp)
        session.commit()
        session.refresh(role_emp)
    
    # Create employee user if not exists
    emp = session.exec(select(SystemUser).where(SystemUser.email == "employee@example.com")).first()
    if not emp:
        emp = SystemUser(
            full_name="Employee Test",
            email="employee@example.com",
            password_hash=hash_password("employeepass"),
            role_id=role_emp.role_id,
            is_active=True,
        )
        session.add(emp)
        session.commit()
        session.refresh(emp)

    r = client.post("/auth/login", json={"email": "employee@example.com", "password": "employeepass"})
    return r.json()["access_token"]

def test_get_tables_empty(client: TestClient, test_data):
    token = _admin_token(client)
    response = client.get("/tables", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []

def test_create_table_success(client: TestClient, session: Session, test_data):
    token = _admin_token(client)
    
    payload = {"table_number": 5, "capacity": 4, "label": "Mesa Principal"}
    response = client.post("/tables", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["table_number"] == 5
    assert data["table_code"] == "T005"
    assert data["capacity"] == 4
    assert data["label"] == "Mesa Principal"
    assert data["status"] == "FREE"

    # Test conflict
    response_conflict = client.post("/tables", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert response_conflict.status_code == 409

def test_update_table(client: TestClient, session: Session, test_data):
    token = _admin_token(client)

    # Setup tables
    table1 = TableSpot(table_number=10, table_code="T010", capacity=2, status="FREE", is_active=True)
    table2 = TableSpot(table_number=11, table_code="T011", capacity=4, status="FREE", is_active=True)
    session.add(table1)
    session.add(table2)
    session.commit()
    session.refresh(table1)
    session.refresh(table2)

    # Update table1 capacity and status
    update_payload = {"capacity": 6, "status": "OCCUPIED"}
    response = client.put(f"/tables/{table1.table_id}", headers={"Authorization": f"Bearer {token}"}, json=update_payload)
    assert response.status_code == 200
    assert response.json()["capacity"] == 6
    assert response.json()["status"] == "OCCUPIED"

    # Try invalid status
    invalid_payload = {"status": "INVALID_STATUS"}
    response_invalid = client.put(f"/tables/{table1.table_id}", headers={"Authorization": f"Bearer {token}"}, json=invalid_payload)
    assert response_invalid.status_code == 400

    # Update table_number to conflict with table2
    conflict_payload = {"table_number": 11}
    response_conflict = client.put(f"/tables/{table1.table_id}", headers={"Authorization": f"Bearer {token}"}, json=conflict_payload)
    assert response_conflict.status_code == 409

    # Update to non-existent table
    response_missing = client.put("/tables/9999", headers={"Authorization": f"Bearer {token}"}, json={"capacity": 5})
    assert response_missing.status_code == 404

def test_delete_table(client: TestClient, session: Session, test_data):
    token = _admin_token(client)

    table = TableSpot(table_number=20, table_code="T020", capacity=4, status="FREE", is_active=True)
    session.add(table)
    session.commit()
    session.refresh(table)

    response = client.delete(f"/tables/{table.table_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Mesa desactivada exitosamente"

    # Verify deactivated
    session.refresh(table)
    assert table.is_active is False

    # Delete non-existent
    response_missing = client.delete("/tables/9999", headers={"Authorization": f"Bearer {token}"})
    assert response_missing.status_code == 404

def test_close_table_and_qr(client: TestClient, session: Session, test_data):
    admin_token = _admin_token(client)
    emp_token = _employee_token(client, session)

    # 1. Create category and product
    cat = Category(category_name="Cafe", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    prod = Product(
        name="Latte Especial",
        category_id=cat.category_id,
        price=10.0,
        stock_quantity=50,
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # 2. Create table
    table = TableSpot(table_number=30, table_code="T030", capacity=4, status="OCCUPIED", is_active=True)
    session.add(table)
    session.commit()
    session.refresh(table)

    # 3. Create active order for table
    admin_user = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    order = Order(
        table_id=table.table_id,
        status="PREPARING",
        total_amount=20.0,
        order_type="DINE_IN",
        system_user_id=admin_user.system_user_id,
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    # Add order item
    item = OrderItem(
        order_id=order.order_id,
        product_id=prod.product_id,
        quantity=2,
        unit_price=10.0,
        subtotal=20.0,
        status="PENDING",
    )
    session.add(item)
    session.commit()

    # 4. Close table via employee endpoint
    close_payload = {"payment_method": "CARD", "tip_amount": 2.0}
    response = client.post(f"/tables/{table.table_id}/close", headers={"Authorization": f"Bearer {emp_token}"}, json=close_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["table_id"] == table.table_id
    assert data["total_amount"] == 20.0
    assert data["tip_amount"] == 2.0
    assert data["payment_method"] == "CARD"
    assert order.order_id in data["order_ids"]

    # Verify table status updated to FREE
    session.refresh(table)
    assert table.status == "FREE"

    # Try closing table that is not occupied
    response_not_occupied = client.post(f"/tables/{table.table_id}/close", headers={"Authorization": f"Bearer {emp_token}"}, json=close_payload)
    assert response_not_occupied.status_code == 400

    # Close non-existent table
    response_missing = client.post("/tables/9999/close", headers={"Authorization": f"Bearer {emp_token}"}, json=close_payload)
    assert response_missing.status_code == 404

    # 5. Generate QR Code
    response_qr = client.get(f"/tables/{table.table_id}/qr", headers={"Authorization": f"Bearer {admin_token}"})
    assert response_qr.status_code == 200
    assert response_qr.headers["content-type"] == "image/png"

    # Generate QR Code for missing table
    response_qr_missing = client.get("/tables/9999/qr", headers={"Authorization": f"Bearer {admin_token}"})
    assert response_qr_missing.status_code == 404
