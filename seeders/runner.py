"""Orquesta los seeders demo. Uso: `python scripts/seed.py`."""

from sqlmodel import Session

from app.core.database import create_db_and_tables, engine

from .catalog import seed_catalog_and_inventory
from .users import seed_demo_users
from .workshops import seed_demo_workshops


def run_all() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        admin_id = seed_demo_users(session)
        seed_catalog_and_inventory(session, admin_id)
        seed_demo_workshops(session)
