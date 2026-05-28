"""
Payment service layer for processing and tracking payments.

This service handles payment creation, processing, refunds, and reporting.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.time import utc_now
from app.models.operations import Order, Payment


def validate_payment_amount(amount: float) -> bool:
    """
    Validate that a payment amount is valid.

    Args:
        amount: Payment amount to validate

    Returns:
        True if amount is valid (positive number with max 2 decimals)
    """
    if amount <= 0:
        return False

    # Check that amount has at most 2 decimal places
    if round(amount, 2) != amount:
        return False

    return True


def create_payment(
    session: Session,
    order_id: int,
    amount: float,
    payment_method: str,
    system_user_id: int,
    customer_id: Optional[int] = None,
    tip_amount: float = 0.0,
    transaction_reference: Optional[str] = None
) -> Payment:
    """
    Create a new payment record.

    Args:
        session: Database session
        order_id: ID of order being paid
        amount: Payment amount
        payment_method: Method of payment (CASH, CARD, TRANSFER, WALLET, CRYPTO)
        system_user_id: ID of cashier/user processing payment
        customer_id: Optional customer ID
        tip_amount: Optional tip amount
        transaction_reference: Optional transaction reference for digital payments

    Returns:
        Created Payment instance

    Raises:
        HTTPException: If validation fails or order not found
    """
    # Validate order exists
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Validate amount
    if not validate_payment_amount(amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment amount. Must be positive number with max 2 decimals"
        )

    # Validate payment method
    valid_methods = ["CASH", "CARD", "TRANSFER", "WALLET", "CRYPTO"]
    if payment_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment method. Must be one of: {', '.join(valid_methods)}"
        )

    # Validate tip amount
    if tip_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tip amount cannot be negative"
        )

    # Create payment
    payment = Payment(
        order_id=order_id,
        customer_id=customer_id,
        payment_method=payment_method,
        amount=round(amount, 2),
        tip_amount=round(tip_amount, 2),
        status="PENDING",
        transaction_reference=transaction_reference,
        system_user_id=system_user_id,
        payment_date=utc_now()
    )

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment


def process_payment(
    session: Session,
    payment_id: int
) -> Payment:
    """
    Process a pending payment (mark as completed).

    Args:
        session: Database session
        payment_id: ID of payment to process

    Returns:
        Updated Payment instance

    Raises:
        HTTPException: If payment not found or already processed
    """
    payment = session.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process payment with status: {payment.status}"
        )

    payment.status = "COMPLETED"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment


def refund_payment(
    session: Session,
    payment_id: int,
    reason: Optional[str] = None
) -> Payment:
    """
    Refund a completed payment.

    Args:
        session: Database session
        payment_id: ID of payment to refund
        reason: Optional reason for refund

    Returns:
        Updated Payment instance

    Raises:
        HTTPException: If payment not found or cannot be refunded
    """
    payment = session.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status not in ["COMPLETED", "PENDING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refund payment with status: {payment.status}"
        )

    payment.status = "REFUNDED"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment


def get_payment_summary(
    session: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    payment_method: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get payment summary statistics for a date range.

    Args:
        session: Database session
        start_date: Optional start date (defaults to today)
        end_date: Optional end date (defaults to today)
        payment_method: Optional filter by payment method

    Returns:
        Dictionary with payment statistics
    """
    from datetime import date as date_cls
    from datetime import datetime

    # Default to today if not specified
    if not start_date:
        start_date = date_cls.today()
    if not end_date:
        end_date = date_cls.today()

    # Build query
    stmt = select(Payment)

    # Filter by date range
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    stmt = stmt.where(
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt
    )

    # Optional filter by payment method
    if payment_method:
        stmt = stmt.where(Payment.payment_method == payment_method)

    # Optional filter by status
    stmt = stmt.where(Payment.status != "REFUNDED")

    payments = session.exec(stmt).all()

    # Calculate statistics
    completed_payments = [p for p in payments if p.status == "COMPLETED"]
    pending_payments = [p for p in payments if p.status == "PENDING"]

    total_amount = sum(p.amount for p in completed_payments)
    total_tips = sum(p.tip_amount for p in completed_payments)
    total_with_tips = total_amount + total_tips

    # Group by payment method
    by_method = {}
    for p in completed_payments:
        if p.payment_method not in by_method:
            by_method[p.payment_method] = {
                "count": 0,
                "total": 0.0,
                "tips": 0.0
            }
        by_method[p.payment_method]["count"] += 1
        by_method[p.payment_method]["total"] += p.amount
        by_method[p.payment_method]["tips"] += p.tip_amount

    return {
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_transactions": len(completed_payments),
            "pending_transactions": len(pending_payments),
            "total_sales": round(total_amount, 2),
            "total_tips": round(total_tips, 2),
            "total_with_tips": round(total_with_tips, 2),
            "average_transaction": round(total_amount / len(completed_payments), 2) if completed_payments else 0.0,
            "average_tip_percentage": round(
                (total_tips / total_amount * 100) if total_amount > 0 else 0, 2
            )
        },
        "by_method": by_method,
        "generated_at": utc_now().isoformat()
    }


def get_payments_for_order(
    session: Session,
    order_id: int
) -> List[Dict[str, Any]]:
    """
    Get all payments associated with an order.

    Args:
        session: Database session
        order_id: ID of order

    Returns:
        List of payment dictionaries
    """
    payments = session.exec(
        select(Payment).where(Payment.order_id == order_id)
    ).all()

    return [
        {
            "payment_id": p.payment_id,
            "order_id": p.order_id,
            "amount": p.amount,
            "tip_amount": p.tip_amount,
            "total": round(p.amount + p.tip_amount, 2),
            "payment_method": p.payment_method,
            "status": p.status,
            "transaction_reference": p.transaction_reference,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None
        }
        for p in payments
    ]


def cancel_payment(
    session: Session,
    payment_id: int,
    reason: Optional[str] = None
) -> Payment:
    """
    Cancel a pending payment.

    Args:
        session: Database session
        payment_id: ID of payment to cancel
        reason: Optional reason for cancellation

    Returns:
        Updated Payment instance

    Raises:
        HTTPException: If payment not found or cannot be cancelled
    """
    payment = session.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only cancel PENDING payments. Current status: {payment.status}"
        )

    payment.status = "CANCELLED"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment
