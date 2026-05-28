from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.catalog import Workshop, WorkshopSchedule, Category
from app.models.crm import WorkshopReservation, Customer
from app.schemas.auth import UserResponse
from app.schemas.workshops import WorkshopCreate, WorkshopResponse, WorkshopUpdate
from app.services.workshop_service import (
    create_workshop as service_create_workshop,
    update_workshop as service_update_workshop,
    get_available_workshops,
    get_workshop_details,
)

WORKSHOP_NOT_FOUND = "Taller no encontrado"

router = APIRouter(tags=["Workshops"])


@router.get("", response_model=List[dict])
def get_workshops(session: Session = Depends(get_db)):
    """Obtiene el catálogo de talleres con formato compatible para el frontend."""
    workshops = session.exec(
        select(Workshop).where(Workshop.is_active == True)
    ).all()
    
    result = []
    for w in workshops:
        schedules = session.exec(
            select(WorkshopSchedule).where(WorkshopSchedule.workshop_id == w.workshop_id)
        ).all()
        w_dict = w.model_dump()
        w_dict["id"] = str(w.workshop_id)
        w_dict["workshop_id"] = w.workshop_id
        
        # Calcular spots para el frontend
        total_available = sum(s.available_slots for s in schedules) if schedules else 0
        w_dict["totalSpots"] = w.max_capacity
        w_dict["reservedSpots"] = max(0, w.max_capacity - total_available)
        
        # Asegurar que el mapeador del frontend (workshops.service.ts) no falle
        schedules_list = []
        if schedules:
            for s in schedules:
                s_dict = s.model_dump()
                s_dict["id"] = str(s.schedule_id)
                # Forzar que el campo se llame exactamente como espera el frontend
                s_dict["schedule_date"] = str(s.schedule_date)
                s_dict["start_time"] = s.start_time.strftime("%H:%M")
                schedules_list.append(s_dict)
        else:
            # Si no hay horarios, creamos uno ficticio para evitar el crash del 'TBD'
            schedules_list.append({
                "id": "0",
                "schedule_date": str(datetime.now().date()),
                "start_time": "00:00",
                "available_slots": w.max_capacity
            })

        w_dict["schedules"] = schedules_list
        result.append(w_dict)
    return result


@router.post("", response_model=WorkshopResponse, status_code=status.HTTP_201_CREATED)
def create_workshop_endpoint(
    workshop_data: WorkshopCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    """Create a new workshop."""
    category = session.get(Category, workshop_data.category_id)
    if not category or category.type != "WORKSHOP":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category or not a workshop category.",
        )

    try:
        # Create workshop using service
        data = {
            "name": workshop_data.name,
            "category_id": workshop_data.category_id,
            "description": workshop_data.description,
            "duration_minutes": workshop_data.duration_minutes,
            "max_capacity": workshop_data.max_capacity,
            "price": workshop_data.price,
            "instructor_name": workshop_data.instructor_name,
            "is_active": workshop_data.is_active,
        }
        
        workshop = service_create_workshop(session, data)

        # Add schedules if provided
        if workshop_data.schedules:
            for sched in workshop_data.schedules:
                schedule = WorkshopSchedule(
                    workshop_id=workshop.workshop_id,
                    schedule_date=sched.schedule_date,
                    start_time=sched.start_time,
                    end_time=sched.end_time,
                    available_slots=sched.available_slots,
                    status=sched.status,
                )
                session.add(schedule)
            session.commit()

        # Re-fetch with schedules loaded to include schedule IDs in response
        workshop_obj = session.get(Workshop, workshop.workshop_id)
        schedules = session.exec(
            select(WorkshopSchedule).where(WorkshopSchedule.workshop_id == workshop.workshop_id)
        ).all()
        response_data = workshop_obj.model_dump() if workshop_obj else {}
        response_data["schedules"] = [schedule.model_dump() for schedule in schedules]
        return WorkshopResponse.model_validate(response_data)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al guardar el taller: {str(e)}"
        )

    # Re-fetch con schedules cargados
    return session.get(Workshop, workshop.workshop_id)


@router.put("/{workshop_id}", response_model=WorkshopResponse, responses={404: {"description": WORKSHOP_NOT_FOUND}})
def update_workshop(
    workshop_id: int,
    workshop_data: WorkshopUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    workshop = session.get(Workshop, workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail=WORKSHOP_NOT_FOUND)

    for key, value in workshop_data.model_dump(exclude_unset=True).items():
        setattr(workshop, key, value)

    session.add(workshop)
    session.commit()
    session.refresh(workshop)

    return session.get(Workshop, workshop_id)


@router.delete("/{workshop_id}", responses={404: {"description": WORKSHOP_NOT_FOUND}})
def delete_workshop(
    workshop_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    """Borrado lógico de un taller."""
    workshop = session.get(Workshop, workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail=WORKSHOP_NOT_FOUND)

    workshop.is_active = False
    session.add(workshop)
    session.commit()
    return {"message": "Taller desactivado correctamente"}


@router.get("/{workshop_id}/reservations")
def get_workshop_reservations(
    workshop_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    """Obtiene las reservaciones con datos del cliente para el frontend."""
    stmt = (
        select(WorkshopReservation, Customer)
        .join(Customer, WorkshopReservation.customer_id == Customer.customer_id)
        .join(WorkshopSchedule, WorkshopReservation.schedule_id == WorkshopSchedule.schedule_id)
        .where(WorkshopSchedule.workshop_id == workshop_id)
    )
    results = session.exec(stmt).all()
    
    reservations = []
    for res, cust in results:
        reservations.append({
            "id": str(res.reservation_id),
            "name": cust.full_name,
            "email": cust.email,
            "phone": cust.phone,
            "attendees": res.quantity_slots,
            "attended": res.status == "ATTENDED",
            "status": res.status
        })
    return reservations


@router.post("/{workshop_id}/reservations", responses={404: {"description": WORKSHOP_NOT_FOUND}})
def create_workshop_reservation(
    workshop_id: int,
    reservation_data: dict,  # full_name, email, phone, schedule_id, attendees
    session: Session = Depends(get_db),
):
    """Crea una reservación real y descuenta cupos del horario."""
    # 1. Verificar horario
    schedule_id = reservation_data.get("schedule_id")
    if not schedule_id:
        raise HTTPException(status_code=400, detail="El 'schedule_id' es obligatorio")

    schedule = session.get(WorkshopSchedule, schedule_id)
    if not schedule or schedule.workshop_id != workshop_id:
        raise HTTPException(status_code=404, detail="Horario no encontrado para este taller")

    workshop = session.get(Workshop, workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail=WORKSHOP_NOT_FOUND)

    attendees = reservation_data.get("attendees", 1)
    if schedule.available_slots < attendees:
        raise HTTPException(status_code=400, detail="No hay suficientes cupos disponibles")

    # 2. Buscar o crear cliente (simplificado)
    customer_email = reservation_data.get("email")
    customer = session.exec(
        select(Customer).where(Customer.email == customer_email)
    ).first()
    if not customer:
        customer = Customer(
            full_name=reservation_data.get("full_name"),
            email=customer_email,
            phone=reservation_data.get("phone"),
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)

    # 3. Crear reservación
    # Hardcoding system_user_id for now as this might be a public booking
    reservation = WorkshopReservation(
        customer_id=customer.customer_id,
        schedule_id=schedule.schedule_id,
        system_user_id=1,
        quantity_slots=attendees,
        total_price=float(workshop.price) * attendees,
        status="CONFIRMED",
    )

    # 4. Actualizar slots
    schedule.available_slots -= attendees
    if schedule.available_slots == 0:
        schedule.status = "FULL"

    session.add(reservation)
    session.add(schedule)
    session.commit()
    session.refresh(reservation)

    return reservation
