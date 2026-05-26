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

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("")
def get_payments(
    date_filter: Optional[str] = Query(None, alias="date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_role(["admin", "cashier", "employee"])),
):
    """Historial de pagos del día (o de la fecha indicada)."""
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()

    start = datetime.combine(filter_date, datetime.min.time())
    end = datetime.combine(filter_date, datetime.max.time())

    payments = session.exec(
        select(Payment)
        .where(Payment.payment_date >= start, Payment.payment_date <= end)
        .order_by(Payment.payment_date.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    result = []
    for p in payments:
        order = session.get(Order, p.order_id)
        table = session.get(TableSpot, order.table_id) if order and order.table_id else None
        user = session.get(SystemUser, p.system_user_id)
        result.append({
            "payment_id": p.payment_id,
            "order_id": p.order_id,
            "table_number": table.table_number if table else None,
            "table_code": table.table_code if table else None,
            "payment_method": p.payment_method,
            "amount": p.amount,
            "tip_amount": p.tip_amount,
            "total": round(p.amount + p.tip_amount, 2),
            "payment_date": p.payment_date.isoformat(),
            "cashier": user.full_name if user else None,
        })

    summary = {
        "count": len(result),
        "total_ventas": round(sum(r["amount"] for r in result), 2),
        "total_propinas": round(sum(r["tip_amount"] for r in result), 2),
        "total_con_propinas": round(sum(r["total"] for r in result), 2),
    }

    return {"payments": result, "summary": summary, "date": filter_date.isoformat()}
