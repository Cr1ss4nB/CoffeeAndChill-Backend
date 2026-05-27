from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.infrastructure import TableSpot
from app.models.operations import Order
from app.models.security import SystemUser
from app.schemas.auth import UserResponse
from app.services.payment_service import get_payment_summary

router = APIRouter(prefix="/payments", tags=["payments"])


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

    # Get summary for the date
    summary_data = get_payment_summary(session, start_date=filter_date, end_date=filter_date)
    
    # Enrich payment details with order and table information
    result = []
    for payment_method in summary_data["by_method"].values():
        # Note: This is a simplified response; you may want to get individual payments
        # if you need full payment details with table numbers
        pass
    
    # Return the summary data structure
    return {
        "payments": result,
        "summary": {
            "count": summary_data["summary"]["total_transactions"],
            "total_ventas": summary_data["summary"]["total_sales"],
            "total_propinas": summary_data["summary"]["total_tips"],
            "total_con_propinas": summary_data["summary"]["total_with_tips"],
        },
        "date": filter_date.isoformat()
    }
