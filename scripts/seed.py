import os
import sys

from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.catalog import Category, Product
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# System user ID used for stock movements in the seed.
# Assumes the first admin user (id=1) exists before running seed.
SEED_USER_ID = 1


def seed_catalog():
    print("Creating tables...")
    create_db_and_tables()

    with Session(engine) as session:
        existing = session.exec(select(Category)).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # ── Categories ────────────────────────────────────────────────────────
        print("Seeding categories...")
        cat_hot = Category(category_name="Bebidas Calientes", type="PRODUCT")
        cat_cold = Category(category_name="Bebidas Frías", type="PRODUCT")
        cat_food = Category(category_name="Pasabocas", type="PRODUCT")
        cat_workshop = Category(category_name="Cerámica", type="WORKSHOP")
        session.add_all([cat_hot, cat_cold, cat_food, cat_workshop])
        session.commit()
        for obj in [cat_hot, cat_cold, cat_food, cat_workshop]:
            session.refresh(obj)

        # ── Products ──────────────────────────────────────────────────────────
        print("Seeding products...")
        products = [
            Product(name="Espresso", category_id=cat_hot.category_id, price=4500, stock_quantity=0,
                    description="Espresso doble de café de especialidad"),
            Product(name="Cappuccino", category_id=cat_hot.category_id, price=6500, stock_quantity=0,
                    description="Espresso con leche vaporizada y espuma"),
            Product(name="Latte", category_id=cat_hot.category_id, price=7000, stock_quantity=0,
                    description="Espresso con leche cremosa vaporizada"),
            Product(name="Americano", category_id=cat_hot.category_id, price=5000, stock_quantity=0,
                    description="Espresso con agua caliente"),
            Product(name="Frappé Café", category_id=cat_cold.category_id, price=9500, stock_quantity=0,
                    description="Café frío con hielo, leche y jarabe"),
            Product(name="Frappé Matcha", category_id=cat_cold.category_id, price=10000, stock_quantity=0,
                    description="Matcha frío con hielo y leche"),
            Product(name="Limonada de Coco", category_id=cat_cold.category_id, price=8000, stock_quantity=0,
                    description="Limonada refrescante con leche de coco"),
            Product(name="Croissant", category_id=cat_food.category_id, price=5500, stock_quantity=30,
                    description="Croissant artesanal de mantequilla"),
            Product(name="Muffin de Arándanos", category_id=cat_food.category_id, price=6000, stock_quantity=20,
                    description="Muffin casero con arándanos frescos"),
        ]
        session.add_all(products)
        session.commit()
        for p in products:
            session.refresh(p)

        # Build lookup by name for easy reference below
        prod = {p.name: p for p in products}

        # ── Ingredients ───────────────────────────────────────────────────────
        print("Seeding ingredients...")
        ingredients_data = [
            Ingredient(name="Café molido", unit="g", min_stock=500,
                       description="Café de especialidad molido medio"),
            Ingredient(name="Leche entera", unit="ml", min_stock=3000),
            Ingredient(name="Leche de coco", unit="ml", min_stock=500),
            Ingredient(name="Jarabe de azúcar", unit="ml", min_stock=500),
            Ingredient(name="Hielo", unit="g", min_stock=2000),
            Ingredient(name="Matcha en polvo", unit="g", min_stock=200),
            Ingredient(name="Agua caliente", unit="ml", min_stock=0),
            Ingredient(name="Limón", unit="units", min_stock=10),
        ]
        session.add_all(ingredients_data)
        session.commit()
        for i in ingredients_data:
            session.refresh(i)

        ing = {i.name: i for i in ingredients_data}

        # ── Initial ingredient stock (IN movements) ───────────────────────────
        print("Seeding initial ingredient stock...")
        initial_stock = [
            (ing["Café molido"],      2000),
            (ing["Leche entera"],    10000),
            (ing["Leche de coco"],    2000),
            (ing["Jarabe de azúcar"], 2000),
            (ing["Hielo"],           10000),
            (ing["Matcha en polvo"],   500),
            (ing["Agua caliente"],       0),  # on demand, no initial stock needed
            (ing["Limón"],              30),
        ]
        for ingredient, qty in initial_stock:
            if qty > 0:
                session.add(
                    IngredientStockMovement(
                        ingredient_id=ingredient.ingredient_id,
                        system_user_id=SEED_USER_ID,
                        movement_type="IN",
                        quantity=qty,
                        notes="Stock inicial (seed)",
                    )
                )
        session.commit()

        # ── Product consumption (default recipes) ─────────────────────────────
        print("Seeding product consumptions...")
        consumptions = [
            # Espresso: 18g café
            ProductConsumption(product_id=prod["Espresso"].product_id,
                               ingredient_id=ing["Café molido"].ingredient_id, quantity_used=18),
            # Cappuccino: 18g café + 120ml leche
            ProductConsumption(product_id=prod["Cappuccino"].product_id,
                               ingredient_id=ing["Café molido"].ingredient_id, quantity_used=18),
            ProductConsumption(product_id=prod["Cappuccino"].product_id,
                               ingredient_id=ing["Leche entera"].ingredient_id, quantity_used=120),
            # Latte: 18g café + 180ml leche
            ProductConsumption(product_id=prod["Latte"].product_id,
                               ingredient_id=ing["Café molido"].ingredient_id, quantity_used=18),
            ProductConsumption(product_id=prod["Latte"].product_id,
                               ingredient_id=ing["Leche entera"].ingredient_id, quantity_used=180),
            # Americano: 18g café + 120ml agua
            ProductConsumption(product_id=prod["Americano"].product_id,
                               ingredient_id=ing["Café molido"].ingredient_id, quantity_used=18),
            ProductConsumption(product_id=prod["Americano"].product_id,
                               ingredient_id=ing["Agua caliente"].ingredient_id, quantity_used=120),
            # Frappé Café: 18g café + 150ml leche + 200g hielo + 30ml jarabe
            ProductConsumption(product_id=prod["Frappé Café"].product_id,
                               ingredient_id=ing["Café molido"].ingredient_id, quantity_used=18),
            ProductConsumption(product_id=prod["Frappé Café"].product_id,
                               ingredient_id=ing["Leche entera"].ingredient_id, quantity_used=150),
            ProductConsumption(product_id=prod["Frappé Café"].product_id,
                               ingredient_id=ing["Hielo"].ingredient_id, quantity_used=200),
            ProductConsumption(product_id=prod["Frappé Café"].product_id,
                               ingredient_id=ing["Jarabe de azúcar"].ingredient_id, quantity_used=30),
            # Frappé Matcha: 8g matcha + 150ml leche + 200g hielo + 20ml jarabe
            ProductConsumption(product_id=prod["Frappé Matcha"].product_id,
                               ingredient_id=ing["Matcha en polvo"].ingredient_id, quantity_used=8),
            ProductConsumption(product_id=prod["Frappé Matcha"].product_id,
                               ingredient_id=ing["Leche entera"].ingredient_id, quantity_used=150),
            ProductConsumption(product_id=prod["Frappé Matcha"].product_id,
                               ingredient_id=ing["Hielo"].ingredient_id, quantity_used=200),
            ProductConsumption(product_id=prod["Frappé Matcha"].product_id,
                               ingredient_id=ing["Jarabe de azúcar"].ingredient_id, quantity_used=20),
            # Limonada de Coco: 2 limones + 150ml leche de coco + 200g hielo + 30ml jarabe
            ProductConsumption(product_id=prod["Limonada de Coco"].product_id,
                               ingredient_id=ing["Limón"].ingredient_id, quantity_used=2),
            ProductConsumption(product_id=prod["Limonada de Coco"].product_id,
                               ingredient_id=ing["Leche de coco"].ingredient_id, quantity_used=150),
            ProductConsumption(product_id=prod["Limonada de Coco"].product_id,
                               ingredient_id=ing["Hielo"].ingredient_id, quantity_used=200),
            ProductConsumption(product_id=prod["Limonada de Coco"].product_id,
                               ingredient_id=ing["Jarabe de azúcar"].ingredient_id, quantity_used=30),
            # Croissant + Muffin: stock-only (no ingredient tracking, stock_quantity manages availability)
        ]
        session.add_all(consumptions)
        session.commit()

        print("Done! Seed complete.")


if __name__ == "__main__":
    seed_catalog()
