"""
Workshop service layer for managing workshops and reservations.

This service handles workshop creation, updates, reservations,
and availability tracking.
"""

from typing import List, Dict, Any, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.catalog import Workshop, WorkshopSchedule
from app.models.crm import WorkshopReservation, Customer
from app.core.time import utc_now


def create_workshop(
    session: Session,
    data: Dict[str, Any]
) -> Workshop:
    """
    Create a new workshop.
    
    Args:
        session: Database session
        data: Dictionary with workshop information
              (name, category_id, description, duration_minutes, max_capacity, price, instructor_name)
    
    Returns:
        Created Workshop instance
    
    Raises:
        HTTPException: If validation fails or category not found
    """
    # Validate required fields
    required_fields = ["name", "category_id", "duration_minutes", "max_capacity", "price"]
    for field in required_fields:
        if field not in data or data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} is required"
            )
    
    # Validate numeric fields
    if data["duration_minutes"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_minutes must be greater than zero"
        )
    
    if data["max_capacity"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_capacity must be greater than zero"
        )
    
    if data["price"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price cannot be negative"
        )
    
    # Create workshop
    workshop = Workshop(
        name=data["name"],
        category_id=data["category_id"],
        description=data.get("description"),
        duration_minutes=data["duration_minutes"],
        max_capacity=data["max_capacity"],
        price=round(data["price"], 2),
        instructor_name=data.get("instructor_name"),
        is_active=True
    )
    
    session.add(workshop)
    session.commit()
    session.refresh(workshop)
    
    return workshop


def update_workshop(
    session: Session,
    workshop_id: int,
    data: Dict[str, Any]
) -> Workshop:
    """
    Update an existing workshop.
    
    Args:
        session: Database session
        workshop_id: ID of workshop to update
        data: Dictionary with fields to update
    
    Returns:
        Updated Workshop instance
    
    Raises:
        HTTPException: If workshop not found or validation fails
    """
    workshop = session.get(Workshop, workshop_id)
    
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found"
        )
    
    # Validate numeric fields if provided
    if "duration_minutes" in data and data["duration_minutes"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_minutes must be greater than zero"
        )
    
    if "max_capacity" in data and data["max_capacity"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_capacity must be greater than zero"
        )
    
    if "price" in data and data["price"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price cannot be negative"
        )
    
    # Update fields
    if "name" in data:
        workshop.name = data["name"]
    
    if "description" in data:
        workshop.description = data["description"]
    
    if "duration_minutes" in data:
        workshop.duration_minutes = data["duration_minutes"]
    
    if "max_capacity" in data:
        workshop.max_capacity = data["max_capacity"]
    
    if "price" in data:
        workshop.price = round(data["price"], 2)
    
    if "instructor_name" in data:
        workshop.instructor_name = data["instructor_name"]
    
    if "is_active" in data:
        workshop.is_active = data["is_active"]
    
    session.add(workshop)
    session.commit()
    session.refresh(workshop)
    
    return workshop


def create_reservation(
    session: Session,
    workshop_id: int,
    customer_id: int,
    system_user_id: int,
    schedule_id: int,
    quantity_slots: int = 1,
    special_requests: Optional[str] = None
) -> WorkshopReservation:
    """
    Create a workshop reservation.
    
    Args:
        session: Database session
        workshop_id: ID of workshop
        customer_id: ID of customer making reservation
        system_user_id: ID of system user processing reservation
        schedule_id: ID of workshop schedule/slot
        quantity_slots: Number of slots to reserve
        special_requests: Optional special requests
    
    Returns:
        Created WorkshopReservation instance
    
    Raises:
        HTTPException: If validation fails or resources not found
    """
    # Validate workshop exists
    workshop = session.get(Workshop, workshop_id)
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found"
        )
    
    # Validate customer exists
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Validate schedule exists
    schedule = session.get(WorkshopSchedule, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop schedule not found"
        )
    
    # Validate quantity
    if quantity_slots <= 0 or quantity_slots > workshop.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantity must be between 1 and {workshop.max_capacity}"
        )
    
    # Check available slots
    if schedule.available_slots < quantity_slots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough slots available. Only {schedule.available_slots} available"
        )
    
    # Calculate total price
    total_price = workshop.price * quantity_slots
    
    # Create reservation
    reservation = WorkshopReservation(
        customer_id=customer_id,
        schedule_id=schedule_id,
        system_user_id=system_user_id,
        quantity_slots=quantity_slots,
        total_price=round(total_price, 2),
        status="PENDING",
        special_requests=special_requests,
        reservation_date=utc_now()
    )
    
    # Update available slots in schedule
    schedule.available_slots -= quantity_slots
    
    session.add(reservation)
    session.add(schedule)
    session.commit()
    session.refresh(reservation)
    
    return reservation


def cancel_reservation(
    session: Session,
    reservation_id: int,
    reason: Optional[str] = None
) -> WorkshopReservation:
    """
    Cancel a workshop reservation.
    
    Args:
        session: Database session
        reservation_id: ID of reservation to cancel
        reason: Optional reason for cancellation
    
    Returns:
        Updated WorkshopReservation instance
    
    Raises:
        HTTPException: If reservation not found or cannot be cancelled
    """
    reservation = session.get(WorkshopReservation, reservation_id)
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )
    
    if reservation.status in ["CANCELLED", "COMPLETED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel reservation with status: {reservation.status}"
        )
    
    # Return slots to schedule
    schedule = session.get(WorkshopSchedule, reservation.schedule_id)
    if schedule:
        schedule.available_slots += reservation.quantity_slots
        session.add(schedule)
    
    reservation.status = "CANCELLED"
    session.add(reservation)
    session.commit()
    session.refresh(reservation)
    
    return reservation


def get_available_workshops(session: Session) -> List[Dict[str, Any]]:
    """
    Get all active workshops with availability information.
    
    Args:
        session: Database session
    
    Returns:
        List of workshop dictionaries with schedule info
    """
    workshops = session.exec(
        select(Workshop).where(Workshop.is_active == True)  # noqa: E712
    ).all()
    
    result = []
    for workshop in workshops:
        # Get schedules with available slots
        schedules = session.exec(
            select(WorkshopSchedule).where(
                WorkshopSchedule.workshop_id == workshop.workshop_id,
                WorkshopSchedule.status == "OPEN"
            )
        ).all()
        
        # Check if any schedule has available slots
        has_availability = any(s.available_slots > 0 for s in schedules)
        
        if has_availability:
            result.append({
                "workshop_id": workshop.workshop_id,
                "name": workshop.name,
                "description": workshop.description,
                "duration_minutes": workshop.duration_minutes,
                "max_capacity": workshop.max_capacity,
                "price": workshop.price,
                "instructor_name": workshop.instructor_name,
                "category_id": workshop.category_id,
                "available_schedules": [
                    {
                        "schedule_id": s.schedule_id,
                        "date": s.schedule_date.isoformat(),
                        "start_time": s.start_time.isoformat(),
                        "end_time": s.end_time.isoformat(),
                        "available_slots": s.available_slots
                    }
                    for s in schedules if s.available_slots > 0
                ]
            })
    
    return result


def get_workshop_details(
    session: Session,
    workshop_id: int
) -> Dict[str, Any]:
    """
    Get detailed information about a workshop including schedules and reservations.
    
    Args:
        session: Database session
        workshop_id: ID of workshop
    
    Returns:
        Dictionary with detailed workshop information
    
    Raises:
        HTTPException: If workshop not found
    """
    workshop = session.get(Workshop, workshop_id)
    
    if not workshop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found"
        )
    
    # Get schedules
    schedules = session.exec(
        select(WorkshopSchedule).where(
            WorkshopSchedule.workshop_id == workshop_id
        )
    ).all()
    
    # Get reservation count
    reservations = session.exec(
        select(WorkshopReservation).where(
            WorkshopReservation.schedule_id.in_([s.schedule_id for s in schedules]),
            WorkshopReservation.status != "CANCELLED"
        )
    ).all()
    
    return {
        "workshop_id": workshop.workshop_id,
        "name": workshop.name,
        "description": workshop.description,
        "duration_minutes": workshop.duration_minutes,
        "max_capacity": workshop.max_capacity,
        "price": workshop.price,
        "instructor_name": workshop.instructor_name,
        "is_active": workshop.is_active,
        "total_reservations": len(reservations),
        "schedules": [
            {
                "schedule_id": s.schedule_id,
                "date": s.schedule_date.isoformat(),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "available_slots": s.available_slots,
                "status": s.status
            }
            for s in schedules
        ]
    }
