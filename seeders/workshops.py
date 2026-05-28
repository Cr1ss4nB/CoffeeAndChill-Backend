"""Seeder de talleres demo y sus horarios."""

from datetime import date, time, timedelta

from sqlmodel import Session, select

from app.models.catalog import Category, Workshop, WorkshopSchedule

_WORKSHOP_CATEGORY_NAME = "Cerámica"

_DEMO_WORKSHOPS: list[dict] = [
    {
        "name": "Taller de Cerámica Inicial",
        "description": "Introducción a modelado manual y acabado básico.",
        "duration_minutes": 120,
        "max_capacity": 12,
        "price": 55000,
        "instructor_name": "Laura Pérez",
        "schedules": [
            {
                "schedule_date": date.today() + timedelta(days=2),
                "start_time": time(9, 0),
                "end_time": time(11, 0),
                "available_slots": 12,
            },
            {
                "schedule_date": date.today() + timedelta(days=9),
                "start_time": time(15, 0),
                "end_time": time(17, 0),
                "available_slots": 12,
            },
        ],
    },
    {
        "name": "Taza Artesanal y Esmaltado",
        "description": "Construye tu propia taza y aprende técnicas de esmaltado.",
        "duration_minutes": 180,
        "max_capacity": 10,
        "price": 68000,
        "instructor_name": "Andrés Gómez",
        "schedules": [
            {
                "schedule_date": date.today() + timedelta(days=4),
                "start_time": time(10, 0),
                "end_time": time(13, 0),
                "available_slots": 10,
            }
        ],
    },
]


def _get_or_create_workshop_category(session: Session) -> Category:
    category = session.exec(
        select(Category).where(Category.category_name == _WORKSHOP_CATEGORY_NAME)
    ).first()
    if category:
        return category

    category = Category(category_name=_WORKSHOP_CATEGORY_NAME, type="WORKSHOP")
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _get_or_create_workshop(session: Session, category_id: int, payload: dict) -> Workshop:
    workshop = session.exec(select(Workshop).where(Workshop.name == payload["name"])).first()
    if workshop:
        return workshop

    workshop = Workshop(
        name=payload["name"],
        category_id=category_id,
        description=payload["description"],
        duration_minutes=payload["duration_minutes"],
        max_capacity=payload["max_capacity"],
        price=payload["price"],
        instructor_name=payload["instructor_name"],
        is_active=True,
    )
    session.add(workshop)
    session.commit()
    session.refresh(workshop)
    return workshop


def _ensure_workshop_schedule(session: Session, workshop_id: int, payload: dict) -> None:
    existing = session.exec(
        select(WorkshopSchedule)
        .where(WorkshopSchedule.workshop_id == workshop_id)
        .where(WorkshopSchedule.schedule_date == payload["schedule_date"])
        .where(WorkshopSchedule.start_time == payload["start_time"])
    ).first()
    if existing:
        return

    schedule = WorkshopSchedule(
        workshop_id=workshop_id,
        schedule_date=payload["schedule_date"],
        start_time=payload["start_time"],
        end_time=payload["end_time"],
        available_slots=payload["available_slots"],
        status="OPEN",
    )
    session.add(schedule)
    session.commit()


def seed_demo_workshops(session: Session) -> None:
    """Crea talleres demo con horarios activos de forma idempotente."""
    category = _get_or_create_workshop_category(session)

    for workshop_payload in _DEMO_WORKSHOPS:
        workshop = _get_or_create_workshop(session, category.category_id, workshop_payload)
        for schedule_payload in workshop_payload["schedules"]:
            _ensure_workshop_schedule(session, workshop.workshop_id, schedule_payload)
