"""
Unit tests for employee_service.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.core.security import hash_password
from app.models.security import Role, SystemUser
from app.services.employee_service import (
    activate_employee,
    assign_role,
    create_employee,
    deactivate_employee,
    get_employee_with_role,
    list_employees,
    update_employee,
)


@pytest.fixture
def setup_roles(session: Session):
    """Create test roles."""
    admin_role = Role(role_name="admin", permissions="[]")
    waiter_role = Role(role_name="waiter", permissions="[]")
    cashier_role = Role(role_name="cashier", permissions="[]")

    session.add(admin_role)
    session.add(waiter_role)
    session.add(cashier_role)
    session.commit()

    return {
        "admin": admin_role,
        "waiter": waiter_role,
        "cashier": cashier_role,
    }


class TestCreateEmployee:
    """Tests for create_employee function."""

    def test_create_employee_success(self, session: Session, setup_roles):
        """Test successful employee creation."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "securepass123",
            "role": "waiter",
            "phone": "555-1234"
        }

        employee = create_employee(session, data)

        assert employee.system_user_id is not None
        assert employee.full_name == "John Doe"
        assert employee.email == "john@example.com"
        assert employee.phone == "555-1234"
        assert employee.is_active is True
        assert employee.role.role_name == "waiter"

    def test_create_employee_duplicate_email(self, session: Session, setup_roles):
        """Test that duplicate email raises error."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "securepass123",
            "role": "waiter"
        }

        create_employee(session, data)

        # Try to create another with same email
        with pytest.raises(HTTPException) as exc_info:
            create_employee(session, data)

        assert exc_info.value.status_code == 409

    def test_create_employee_invalid_role(self, session: Session):
        """Test that invalid role raises error."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "securepass123",
            "role": "invalid_role"
        }

        with pytest.raises(HTTPException) as exc_info:
            create_employee(session, data)

        assert exc_info.value.status_code == 400

    def test_create_employee_missing_required_field(self, session: Session):
        """Test that missing required fields raise error."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            # password is missing
            "role": "waiter"
        }

        with pytest.raises(HTTPException) as exc_info:
            create_employee(session, data)

        assert exc_info.value.status_code == 400


class TestUpdateEmployee:
    """Tests for update_employee function."""

    def test_update_employee_success(self, session: Session, setup_roles):
        """Test successful employee update."""
        # Create initial employee
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "securepass123",
            "role": "waiter"
        }
        employee = create_employee(session, data)

        # Update employee
        update_data = {
            "full_name": "Jane Doe",
            "phone": "555-9999"
        }
        updated = update_employee(session, employee.system_user_id, update_data)

        assert updated.full_name == "Jane Doe"
        assert updated.phone == "555-9999"
        assert updated.email == "john@example.com"  # Unchanged

    def test_update_employee_email_duplicate(self, session: Session, setup_roles):
        """Test that updating to duplicate email raises error."""
        data1 = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        data2 = {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "pass123",
            "role": "waiter"
        }

        emp1 = create_employee(session, data1)
        emp2 = create_employee(session, data2)

        # Try to update emp2 to have emp1's email
        with pytest.raises(HTTPException) as exc_info:
            update_employee(session, emp2.system_user_id, {"email": "john@example.com"})

        assert exc_info.value.status_code == 409

    def test_update_employee_not_found(self, session: Session):
        """Test that updating non-existent employee raises error."""
        with pytest.raises(HTTPException) as exc_info:
            update_employee(session, 999, {"full_name": "New Name"})

        assert exc_info.value.status_code == 404


class TestGetEmployeeWithRole:
    """Tests for get_employee_with_role function."""

    def test_get_employee_with_role_success(self, session: Session, setup_roles):
        """Test successful retrieval of employee with role."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "securepass123",
            "role": "cashier"
        }
        employee = create_employee(session, data)

        result = get_employee_with_role(session, employee.system_user_id)

        assert result["full_name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert result["role"]["role_name"] == "cashier"
        assert result["is_active"] is True

    def test_get_employee_not_found(self, session: Session):
        """Test that non-existent employee raises error."""
        with pytest.raises(HTTPException) as exc_info:
            get_employee_with_role(session, 999)

        assert exc_info.value.status_code == 404


class TestListEmployees:
    """Tests for list_employees function."""

    def test_list_employees_success(self, session: Session, setup_roles):
        """Test successful employee listing."""
        # Create multiple employees
        data1 = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        data2 = {
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "password": "pass123",
            "role": "cashier"
        }

        create_employee(session, data1)
        create_employee(session, data2)

        employees = list_employees(session, active_only=False)

        assert len(employees) == 2
        assert employees[0]["full_name"] in ["John Doe", "Jane Smith"]
        assert employees[1]["full_name"] in ["John Doe", "Jane Smith"]

    def test_list_employees_active_only(self, session: Session, setup_roles):
        """Test listing only active employees."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }

        emp = create_employee(session, data)
        deactivate_employee(session, emp.system_user_id)

        active = list_employees(session, active_only=True)
        all_employees = list_employees(session, active_only=False)

        assert len(active) == 0
        assert len(all_employees) == 1


class TestActivateDeactivate:
    """Tests for activate_employee and deactivate_employee functions."""

    def test_deactivate_employee(self, session: Session, setup_roles):
        """Test deactivating an employee."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        emp = create_employee(session, data)

        deactivated = deactivate_employee(session, emp.system_user_id)

        assert deactivated.is_active is False

    def test_activate_employee(self, session: Session, setup_roles):
        """Test activating a deactivated employee."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        emp = create_employee(session, data)
        deactivate_employee(session, emp.system_user_id)

        activated = activate_employee(session, emp.system_user_id)

        assert activated.is_active is True


class TestAssignRole:
    """Tests for assign_role function."""

    def test_assign_role_success(self, session: Session, setup_roles):
        """Test successful role assignment."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        emp = create_employee(session, data)

        # Get the cashier role from the fixture
        cashier_role = setup_roles["cashier"]

        assigned = assign_role(session, emp.system_user_id, cashier_role.role_id)

        assert assigned.role_id == cashier_role.role_id
        assert assigned.role.role_name == "cashier"

    def test_assign_role_not_found(self, session: Session, setup_roles):
        """Test assigning role to non-existent employee."""
        admin_role = setup_roles["admin"]

        with pytest.raises(HTTPException) as exc_info:
            assign_role(session, 999, admin_role.role_id)

        assert exc_info.value.status_code == 404

    def test_assign_invalid_role(self, session: Session, setup_roles):
        """Test assigning non-existent role."""
        data = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "pass123",
            "role": "waiter"
        }
        emp = create_employee(session, data)

        with pytest.raises(HTTPException) as exc_info:
            assign_role(session, emp.system_user_id, 999)

        assert exc_info.value.status_code == 404
