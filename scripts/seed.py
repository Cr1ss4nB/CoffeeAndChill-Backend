import os
import sys

from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.catalog import Category, Product

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_catalog():
    print("Creating tables...")
    create_db_and_tables()

    with Session(engine) as session:
        # Check if already seeded
        existing = session.exec(select(Category)).first()
        if existing:
            print("Database already seeded.")
            return

        print("Seeding categories...")
        cat1 = Category(category_name="Bebidas Calientes", type="PRODUCT")
        cat2 = Category(category_name="Bebidas Frías", type="PRODUCT")
        cat3 = Category(category_name="Cerámica", type="WORKSHOP")
        session.add_all([cat1, cat2, cat3])
        session.commit()
        session.refresh(cat1)
        session.refresh(cat2)

        print("Seeding products...")
        p1 = Product(name="Espresso", category_id=cat1.category_id,
                     price=450.00, stock_quantity=1000)
        p2 = Product(name="Cappuccino", category_id=cat1.category_id,
                     price=650.00, stock_quantity=500)
        p3 = Product(name="Cheesecake", category_id=cat2.category_id,
                     price=1200.00, stock_quantity=12)
        session.add_all([p1, p2, p3])
        session.commit()

        print("Done!")


if __name__ == "__main__":
    seed_catalog()
