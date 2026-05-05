"""
Orquesta todos los seeders. Uso: `python scripts/seed.py` o `python -c "from seeders import run_all; run_all()"`.
"""

from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from .catalog import seed_catalog_and_inventory
from .users import seed_demo_users


def run_all() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        admin_id = seed_demo_users(session)
        seed_catalog_and_inventory(session, admin_id)
