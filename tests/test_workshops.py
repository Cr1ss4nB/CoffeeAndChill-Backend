import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Workshop, WorkshopSchedule
from app.models.crm import Customer
from app.models.operations import Order, OrderItem
from app.models.security import SystemUser, Role
from app.core.security import hash_password

# Helper to get auth tokens
def _admin_token(client: TestClient) -> str:
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
    return r.json()["access_token"]

def _employee_token(client: TestClient, session: Session) -> str:
    # Ensure employee role exists
    role = session.exec(select(Role).where(Role.role_name == "employee")).first()
    if not role:
        role = Role(role_name="employee")
        session.add(role)
        session.commit()
        session.refresh(role)
    # Ensure employee user exists
    emp = session.exec(select(SystemUser).where(SystemUser.email == "employee@example.com")).first()
    if not emp:
        emp = SystemUser(
            full_name="Employee Test",
            email="employee@example.com",
            password_hash=hash_password("employeepass"),
            role_id=role.role_id,
            is_active=True,
        )
        session.add(emp)
        session.commit()
        session.refresh(emp)
    r = client.post("/auth/login", json={"email": "employee@example.com", "password": "employeepass"})
    return r.json()["access_token"]

def test_workshop_crud_and_reservations(client: TestClient, session: Session, test_data):
    admin_token = _admin_token(client)
    emp_token = _employee_token(client, session)

    # 1️⃣ Create a workshop category
    workshop_cat = Category(category_name="Talleres", type="WORKSHOP")
    session.add(workshop_cat)
    session.commit()
    session.refresh(workshop_cat)

    # 2️⃣ Create a workshop with schedules via API
    payload = {
        "name": "Taller de Latte",
        "category_id": workshop_cat.category_id,
        "description": "Aprende a preparar latte",
        "duration_minutes": 120,
        "max_capacity": 5,
        "price": 15.0,
        "instructor_name": "Barista Juan",
        "is_active": True,
        "schedules": [
            {
                "schedule_date": "2026-06-01",
                "start_time": "10:00",
                "end_time": "12:00",
                "available_slots": 5,
                "status": "OPEN",
            }
        ],
    }
    r = client.post(
        "/workshops",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert r.status_code == 201
    workshop_resp = r.json()
    workshop_id = workshop_resp["workshop_id"]
    schedule_id = workshop_resp["schedules"][0]["schedule_id"]

    # 3️⃣ Get workshops list – ensure transformed fields exist
    r = client.get("/workshops", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert any(w["workshop_id"] == workshop_id for w in data)
    # front‑end mapping fields
    w = next(w for w in data if w["workshop_id"] == workshop_id)
    assert w["totalSpots"] == w["max_capacity"]
    assert w["reservedSpots"] == 0

    # 4️⃣ Update workshop
    update_payload = {"price": 20.0, "max_capacity": 6}
    r = client.put(
        f"/workshops/{workshop_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=update_payload,
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["price"] == 20.0
    assert updated["max_capacity"] == 6

    # 5️⃣ Create a reservation as employee (public booking)
    reservation_payload = {
        "schedule_id": schedule_id,
        "full_name": "Cliente Test",
        "email": "cliente@example.com",
        "phone": "123456789",
        "attendees": 2,
    }
    r = client.post(
        f"/workshops/{workshop_id}/reservations",
        headers={"Authorization": f"Bearer {emp_token}"},
        json=reservation_payload,
    )
    assert r.status_code == 200
    reservation = r.json()
    assert reservation["quantity_slots"] == 2

    # 6️⃣ Get reservations for workshop
    r = client.get(
        f"/workshops/{workshop_id}/reservations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    reservations = r.json()
    assert any(res["email"] == "cliente@example.com" for res in reservations)

    # 7️⃣ Logical delete workshop
    r = client.delete(
        f"/workshops/{workshop_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Taller desactivado correctamente"

    # Verify the workshop is inactive
    w_obj = session.get(Workshop, workshop_id)
    assert w_obj.is_active is False
