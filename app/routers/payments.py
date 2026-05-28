from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.infrastructure import TableSpot
from app.models.operations import Order, Payment
from app.models.security import SystemUser
from app.schemas.auth import UserResponse

router = APIRouter(tags=["payments"])


@router.get("")
def get_payments(
    date_filter: Optional[str] = Query(None, alias="date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role(["admin", "cashier", "employee"])),
):
    """Get payment history for the specified date (or today by default)."""
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()

    start_dt = datetime.combine(filter_date, datetime.min.time())
    end_dt = datetime.combine(filter_date, datetime.max.time())

    payments = session.exec(
        select(Payment)
        .where(Payment.payment_date >= start_dt, Payment.payment_date <= end_dt)
        .order_by(Payment.payment_date.desc())
    ).all()

    result = []
    for payment in payments[offset:offset + limit]:
        order = session.get(Order, payment.order_id)
        table = session.get(TableSpot, order.table_id) if order and order.table_id else None
        result.append({
            "payment_id": payment.payment_id,
            "order_id": payment.order_id,
            "amount": payment.amount,
            "tip_amount": payment.tip_amount,
            "payment_method": payment.payment_method,
            "status": payment.status,
            "transaction_reference": payment.transaction_reference,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "table_number": table.table_number if table else None,
            "table_code": table.table_code if table else None,
        })

    total_sales = round(sum(p.amount for p in payments), 2)
    total_tips = round(sum(p.tip_amount for p in payments), 2)
    return {
        "payments": result,
        "summary": {
            "count": len(payments),
            "total_ventas": total_sales,
            "total_propinas": total_tips,
            "total_con_propinas": round(total_sales + total_tips, 2),
        },
        "date": filter_date.isoformat()
    }
