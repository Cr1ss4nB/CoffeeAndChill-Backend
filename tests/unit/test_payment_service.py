"""
Unit tests for payment_service.
"""

import pytest
from datetime import datetime, date, time
from fastapi import HTTPException
from sqlmodel import Session

from app.models.operations import Order, Payment
from app.models.security import SystemUser, Role
from app.models.crm import Customer
from app.services.payment_service import (
    validate_payment_amount,
    create_payment,
    process_payment,
    refund_payment,
    get_payment_summary,
    get_payments_for_order,
    cancel_payment,
)
from app.core.security import hash_password


@pytest.fixture
def setup_test_data(session: Session):
    """Create test data for payment tests."""
    # Create roles
    admin_role = Role(role_name="admin", permissions="[]")
    session.add(admin_role)
    session.commit()
    
    # Create system user (cashier)
    cashier = SystemUser(
        full_name="Test Cashier",
        email="cashier@example.com",
        password_hash=hash_password("password"),
        role_id=admin_role.role_id,
        is_active=True
    )
    session.add(cashier)
    session.commit()
    
    # Create customer
    customer = Customer(
        full_name="Test Customer",
        email="customer@example.com",
        is_registered=True
    )
    session.add(customer)
    session.commit()
    
    # Create orders
    order1 = Order(
        customer_id=customer.customer_id,
        system_user_id=cashier.system_user_id,
        order_type="DINE_IN",
        status="COMPLETED",
        subtotal=50.0,
        total_amount=50.0
    )
    order2 = Order(
        customer_id=customer.customer_id,
        system_user_id=cashier.system_user_id,
        order_type="TAKEAWAY",
        status="COMPLETED",
        subtotal=30.0,
        total_amount=30.0
    )
    session.add(order1)
    session.add(order2)
    session.commit()
    
    return {
        "cashier": cashier,
        "customer": customer,
        "order1": order1,
        "order2": order2,
    }


class TestValidatePaymentAmount:
    """Tests for validate_payment_amount function."""
    
    def test_validate_positive_amount(self):
        """Test validation of positive amounts."""
        assert validate_payment_amount(50.0) is True
        assert validate_payment_amount(100.99) is True
        assert validate_payment_amount(0.01) is True
    
    def test_validate_negative_amount(self):
        """Test that negative amounts are invalid."""
        assert validate_payment_amount(-50.0) is False
        assert validate_payment_amount(-0.01) is False
    
    def test_validate_zero_amount(self):
        """Test that zero is invalid."""
        assert validate_payment_amount(0.0) is False
    
    def test_validate_excessive_decimals(self):
        """Test that more than 2 decimals are invalid."""
        assert validate_payment_amount(50.999) is False
        assert validate_payment_amount(100.123) is False


class TestCreatePayment:
    """Tests for create_payment function."""
    
    def test_create_payment_success(self, session: Session, setup_test_data):
        """Test successful payment creation."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        customer = setup_test_data["customer"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CARD",
            cashier.system_user_id,
            customer.customer_id,
            tip_amount=10.0,
            transaction_reference="TXN123"
        )
        
        assert payment.order_id == order.order_id
        assert payment.amount == 100.0
        assert payment.tip_amount == 10.0
        assert payment.payment_method == "CARD"
        assert payment.status == "PENDING"
        assert payment.transaction_reference == "TXN123"
    
    def test_create_payment_invalid_method(self, session: Session, setup_test_data):
        """Test that invalid payment method raises error."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                session,
                order.order_id,
                100.0,
                "INVALID_METHOD",
                cashier.system_user_id
            )
        
        assert exc_info.value.status_code == 400
    
    def test_create_payment_invalid_amount(self, session: Session, setup_test_data):
        """Test that invalid amount raises error."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                session,
                order.order_id,
                -100.0,
                "CASH",
                cashier.system_user_id
            )
        
        assert exc_info.value.status_code == 400
    
    def test_create_payment_order_not_found(self, session: Session, setup_test_data):
        """Test that non-existent order raises error."""
        cashier = setup_test_data["cashier"]
        
        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                session,
                999,
                100.0,
                "CASH",
                cashier.system_user_id
            )
        
        assert exc_info.value.status_code == 404


class TestProcessPayment:
    """Tests for process_payment function."""
    
    def test_process_payment_success(self, session: Session, setup_test_data):
        """Test successful payment processing."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CASH",
            cashier.system_user_id
        )
        
        processed = process_payment(session, payment.payment_id)
        
        assert processed.status == "COMPLETED"
    
    def test_process_payment_already_completed(self, session: Session, setup_test_data):
        """Test that processing already completed payment raises error."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CASH",
            cashier.system_user_id
        )
        
        process_payment(session, payment.payment_id)
        
        with pytest.raises(HTTPException) as exc_info:
            process_payment(session, payment.payment_id)
        
        assert exc_info.value.status_code == 400
    
    def test_process_payment_not_found(self, session: Session):
        """Test that processing non-existent payment raises error."""
        with pytest.raises(HTTPException) as exc_info:
            process_payment(session, 999)
        
        assert exc_info.value.status_code == 404


class TestRefundPayment:
    """Tests for refund_payment function."""
    
    def test_refund_completed_payment(self, session: Session, setup_test_data):
        """Test refunding a completed payment."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CARD",
            cashier.system_user_id
        )
        
        process_payment(session, payment.payment_id)
        refunded = refund_payment(session, payment.payment_id, "Customer requested")
        
        assert refunded.status == "REFUNDED"
    
    def test_refund_pending_payment(self, session: Session, setup_test_data):
        """Test refunding a pending payment."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CARD",
            cashier.system_user_id
        )
        
        refunded = refund_payment(session, payment.payment_id)
        
        assert refunded.status == "REFUNDED"
    
    def test_refund_payment_not_found(self, session: Session):
        """Test that refunding non-existent payment raises error."""
        with pytest.raises(HTTPException) as exc_info:
            refund_payment(session, 999)
        
        assert exc_info.value.status_code == 404


class TestGetPaymentSummary:
    """Tests for get_payment_summary function."""
    
    def test_get_payment_summary_today(self, session: Session, setup_test_data):
        """Test getting payment summary for today."""
        order1 = setup_test_data["order1"]
        order2 = setup_test_data["order2"]
        cashier = setup_test_data["cashier"]
        
        # Create and process payments
        p1 = create_payment(session, order1.order_id, 50.0, "CASH", cashier.system_user_id)
        p2 = create_payment(session, order2.order_id, 30.0, "CARD", cashier.system_user_id, tip_amount=5.0)
        
        process_payment(session, p1.payment_id)
        process_payment(session, p2.payment_id)
        
        summary = get_payment_summary(session)
        
        assert summary["summary"]["total_transactions"] == 2
        assert summary["summary"]["total_sales"] == 80.0
        assert summary["summary"]["total_tips"] == 5.0
    
    def test_get_payment_summary_by_method(self, session: Session, setup_test_data):
        """Test payment summary grouped by method."""
        order1 = setup_test_data["order1"]
        order2 = setup_test_data["order2"]
        cashier = setup_test_data["cashier"]
        
        p1 = create_payment(session, order1.order_id, 50.0, "CASH", cashier.system_user_id)
        p2 = create_payment(session, order2.order_id, 30.0, "CARD", cashier.system_user_id)
        
        process_payment(session, p1.payment_id)
        process_payment(session, p2.payment_id)
        
        summary = get_payment_summary(session)
        
        assert "CASH" in summary["by_method"]
        assert "CARD" in summary["by_method"]
        assert summary["by_method"]["CASH"]["count"] == 1
        assert summary["by_method"]["CARD"]["count"] == 1


class TestGetPaymentsForOrder:
    """Tests for get_payments_for_order function."""
    
    def test_get_payments_for_order(self, session: Session, setup_test_data):
        """Test getting payments for a specific order."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        p1 = create_payment(session, order.order_id, 50.0, "CASH", cashier.system_user_id, tip_amount=5.0)
        
        payments = get_payments_for_order(session, order.order_id)
        
        assert len(payments) == 1
        assert payments[0]["amount"] == 50.0
        assert payments[0]["tip_amount"] == 5.0
        assert payments[0]["total"] == 55.0


class TestCancelPayment:
    """Tests for cancel_payment function."""
    
    def test_cancel_pending_payment(self, session: Session, setup_test_data):
        """Test cancelling a pending payment."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CARD",
            cashier.system_user_id
        )
        
        cancelled = cancel_payment(session, payment.payment_id)
        
        assert cancelled.status == "CANCELLED"
    
    def test_cancel_completed_payment(self, session: Session, setup_test_data):
        """Test that cancelling completed payment raises error."""
        order = setup_test_data["order1"]
        cashier = setup_test_data["cashier"]
        
        payment = create_payment(
            session,
            order.order_id,
            100.0,
            "CARD",
            cashier.system_user_id
        )
        
        process_payment(session, payment.payment_id)
        
        with pytest.raises(HTTPException) as exc_info:
            cancel_payment(session, payment.payment_id)
        
        assert exc_info.value.status_code == 400
