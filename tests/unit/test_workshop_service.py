"""
Unit tests for workshop_service.
"""

from datetime import date, datetime, time, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.core.security import hash_password
from app.models.catalog import Category, Workshop, WorkshopSchedule
from app.models.crm import Customer, WorkshopReservation
from app.models.security import Role, SystemUser
from app.services.workshop_service import (
    cancel_reservation,
    create_reservation,
    create_workshop,
    get_available_workshops,
    get_workshop_details,
    update_workshop,
)


@pytest.fixture
def setup_workshop_data(session: Session):
    """Create test data for workshop tests."""
    # Create category
    category = Category(category_name="Arts & Crafts", type="WORKSHOP", is_active=True)
    session.add(category)
    session.commit()

    # Create role
    admin_role = Role(role_name="admin", permissions="[]")
    session.add(admin_role)
    session.commit()

    # Create system user
    admin = SystemUser(
        full_name="Test Admin",
        email="admin@example.com",
        password_hash=hash_password("password"),
        role_id=admin_role.role_id,
        is_active=True
    )
    session.add(admin)
    session.commit()

    # Create customer
    customer = Customer(
        full_name="Test Customer",
        email="customer@example.com",
        is_registered=True
    )
    session.add(customer)
    session.commit()

    return {
        "category": category,
        "admin": admin,
        "customer": customer,
    }


class TestCreateWorkshop:
    """Tests for create_workshop function."""

    def test_create_workshop_success(self, session: Session, setup_workshop_data):
        """Test successful workshop creation."""
        category = setup_workshop_data["category"]

        data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "description": "Learn basic pottery techniques",
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
            "instructor_name": "John Smith"
        }

        workshop = create_workshop(session, data)

        assert workshop.workshop_id is not None
        assert workshop.name == "Pottery Basics"
        assert workshop.duration_minutes == 120
        assert workshop.max_capacity == 10
        assert workshop.price == 50.0
        assert workshop.is_active is True

    def test_create_workshop_missing_required_field(self, session: Session, setup_workshop_data):
        """Test that missing required field raises error."""
        category = setup_workshop_data["category"]

        data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            # Missing duration_minutes
            "max_capacity": 10,
            "price": 50.0,
        }

        with pytest.raises(HTTPException) as exc_info:
            create_workshop(session, data)

        assert exc_info.value.status_code == 400

    def test_create_workshop_invalid_duration(self, session: Session, setup_workshop_data):
        """Test that invalid duration raises error."""
        category = setup_workshop_data["category"]

        data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 0,  # Invalid
            "max_capacity": 10,
            "price": 50.0,
        }

        with pytest.raises(HTTPException) as exc_info:
            create_workshop(session, data)

        assert exc_info.value.status_code == 400

    def test_create_workshop_negative_price(self, session: Session, setup_workshop_data):
        """Test that negative price raises error."""
        category = setup_workshop_data["category"]

        data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": -50.0,  # Invalid
        }

        with pytest.raises(HTTPException) as exc_info:
            create_workshop(session, data)

        assert exc_info.value.status_code == 400


class TestUpdateWorkshop:
    """Tests for update_workshop function."""

    def test_update_workshop_success(self, session: Session, setup_workshop_data):
        """Test successful workshop update."""
        category = setup_workshop_data["category"]

        data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }

        workshop = create_workshop(session, data)

        # Update workshop
        update_data = {
            "name": "Advanced Pottery",
            "price": 75.0,
            "duration_minutes": 180
        }

        updated = update_workshop(session, workshop.workshop_id, update_data)

        assert updated.name == "Advanced Pottery"
        assert updated.price == 75.0
        assert updated.duration_minutes == 180

    def test_update_workshop_not_found(self, session: Session):
        """Test that updating non-existent workshop raises error."""
        with pytest.raises(HTTPException) as exc_info:
            update_workshop(session, 999, {"name": "New Name"})

        assert exc_info.value.status_code == 404


class TestCreateReservation:
    """Tests for create_reservation function."""

    def test_create_reservation_success(self, session: Session, setup_workshop_data):
        """Test successful reservation creation."""
        category = setup_workshop_data["category"]
        customer = setup_workshop_data["customer"]
        admin = setup_workshop_data["admin"]

        # Create workshop
        workshop_data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }
        workshop = create_workshop(session, workshop_data)

        # Create schedule
        tomorrow = date.today() + timedelta(days=1)
        schedule = WorkshopSchedule(
            workshop_id=workshop.workshop_id,
            schedule_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            available_slots=10,
            status="OPEN"
        )
        session.add(schedule)
        session.commit()

        # Create reservation
        reservation = create_reservation(
            session,
            workshop.workshop_id,
            customer.customer_id,
            admin.system_user_id,
            schedule.schedule_id,
            quantity_slots=2,
            special_requests="Vegetarian meals"
        )

        assert reservation.reservation_id is not None
        assert reservation.customer_id == customer.customer_id
        assert reservation.quantity_slots == 2
        assert reservation.total_price == 100.0
        assert reservation.status == "PENDING"

    def test_create_reservation_insufficient_slots(self, session: Session, setup_workshop_data):
        """Test that reserving more slots than available raises error."""
        category = setup_workshop_data["category"]
        customer = setup_workshop_data["customer"]
        admin = setup_workshop_data["admin"]

        # Create workshop
        workshop_data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }
        workshop = create_workshop(session, workshop_data)

        # Create schedule with limited slots
        tomorrow = date.today() + timedelta(days=1)
        schedule = WorkshopSchedule(
            workshop_id=workshop.workshop_id,
            schedule_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            available_slots=2,
            status="OPEN"
        )
        session.add(schedule)
        session.commit()

        # Try to reserve more than available
        with pytest.raises(HTTPException) as exc_info:
            create_reservation(
                session,
                workshop.workshop_id,
                customer.customer_id,
                admin.system_user_id,
                schedule.schedule_id,
                quantity_slots=5
            )

        assert exc_info.value.status_code == 400


class TestCancelReservation:
    """Tests for cancel_reservation function."""

    def test_cancel_reservation_success(self, session: Session, setup_workshop_data):
        """Test successful reservation cancellation."""
        category = setup_workshop_data["category"]
        customer = setup_workshop_data["customer"]
        admin = setup_workshop_data["admin"]

        # Create and setup workshop
        workshop_data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }
        workshop = create_workshop(session, workshop_data)

        tomorrow = date.today() + timedelta(days=1)
        schedule = WorkshopSchedule(
            workshop_id=workshop.workshop_id,
            schedule_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            available_slots=10,
            status="OPEN"
        )
        session.add(schedule)
        session.commit()

        # Create reservation
        reservation = create_reservation(
            session,
            workshop.workshop_id,
            customer.customer_id,
            admin.system_user_id,
            schedule.schedule_id,
            quantity_slots=2
        )

        # Cancel reservation
        cancelled = cancel_reservation(session, reservation.reservation_id)

        assert cancelled.status == "CANCELLED"

        # Check slots were returned
        session.refresh(schedule)
        assert schedule.available_slots == 10  # Restored

    def test_cancel_reservation_not_found(self, session: Session):
        """Test that cancelling non-existent reservation raises error."""
        with pytest.raises(HTTPException) as exc_info:
            cancel_reservation(session, 999)

        assert exc_info.value.status_code == 404


class TestGetAvailableWorkshops:
    """Tests for get_available_workshops function."""

    def test_get_available_workshops(self, session: Session, setup_workshop_data):
        """Test retrieving available workshops."""
        category = setup_workshop_data["category"]

        # Create active workshop
        workshop_data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }
        workshop = create_workshop(session, workshop_data)

        # Create schedule with available slots
        tomorrow = date.today() + timedelta(days=1)
        schedule = WorkshopSchedule(
            workshop_id=workshop.workshop_id,
            schedule_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            available_slots=5,
            status="OPEN"
        )
        session.add(schedule)
        session.commit()

        available = get_available_workshops(session)

        assert len(available) == 1
        assert available[0]["name"] == "Pottery Basics"
        assert len(available[0]["available_schedules"]) == 1
        assert available[0]["available_schedules"][0]["available_slots"] == 5


class TestGetWorkshopDetails:
    """Tests for get_workshop_details function."""

    def test_get_workshop_details_success(self, session: Session, setup_workshop_data):
        """Test retrieving workshop details."""
        category = setup_workshop_data["category"]

        workshop_data = {
            "name": "Pottery Basics",
            "category_id": category.category_id,
            "duration_minutes": 120,
            "max_capacity": 10,
            "price": 50.0,
        }
        workshop = create_workshop(session, workshop_data)

        details = get_workshop_details(session, workshop.workshop_id)

        assert details["name"] == "Pottery Basics"
        assert details["max_capacity"] == 10
        assert details["price"] == 50.0
        assert details["is_active"] is True

    def test_get_workshop_details_not_found(self, session: Session):
        """Test that retrieving non-existent workshop raises error."""
        with pytest.raises(HTTPException) as exc_info:
            get_workshop_details(session, 999)

        assert exc_info.value.status_code == 404
