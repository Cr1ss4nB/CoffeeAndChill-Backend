"""Seeder temporal de datos amplios para demo y pruebas de frontend.

Ejecuta:
    python scripts/seed_full_demo_temp.py

Es idempotente en la mayoría de entidades base (roles, usuarios, catálogo,
mesas, talleres, reservas) y deja trazas únicas para pedidos, pagos e
invoices para evitar duplicados al re-ejecutarlo.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

from sqlmodel import Session, select

from app.core.dependencies import PERMISSIONS
from app.core.database import create_db_and_tables, engine
from app.core.security import hash_password
from app.models.catalog import Category, Product, Workshop, WorkshopSchedule
from app.models.crm import ActivityLog, Customer, Notification, WorkshopReservation
from app.models.infrastructure import TableSpot, TableZone
from app.models.inventory import Ingredient, IngredientStockMovement, InventoryMovement, ProductConsumption
from app.models.operations import Invoice, Order, Payment
from app.models.security import Role, SystemUser
from app.schemas.auth import UserResponse
from app.schemas.order import CheckoutRequest, OrderItemCreate
from app.services.order_service import process_checkout


SEED_PREFIX = "[SEED-FULL]"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass"
CLIENT_EMAIL = "customer@example.com"
CLIENT_PASSWORD = "customerpass"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": list(PERMISSIONS.keys()),
    "manager": [
        "inventory:view",
        "inventory:adjust",
        "inventory:manage",
        "products:view",
        "products:create",
        "products:edit",
        "products:delete",
        "movements:view",
        "movements:export",
        "users:manage",
        "employees:manage",
        "tables:manage",
        "roles:manage",
        "catalog:manage",
        "workshops:manage",
        "ingredients:view",
        "ingredients:manage",
        "ingredients:adjust",
        "consumption:manage",
    ],
    "cashier": ["movements:view"],
    "waiter": ["tables:manage"],
    "kitchen": ["inventory:view", "movements:view"],
}

EXTRA_PRODUCT_CATEGORIES: list[tuple[str, str]] = [
    ("Postres Artesanales", "PRODUCT"),
    ("Sándwiches", "PRODUCT"),
    ("Especiales Fríos", "PRODUCT"),
    ("Tés e Infusiones", "PRODUCT"),
]

EXTRA_INGREDIENTS: list[tuple[str, str, float, str | None]] = [
    ("Leche de avena", "ml", 2000, "Bebida vegetal para lattes"),
    ("Jarabe de vainilla", "ml", 1500, None),
    ("Jarabe de chocolate", "ml", 1500, None),
    ("Cacao en polvo", "g", 800, None),
    ("Té negro", "g", 500, None),
    ("Té verde", "g", 500, None),
    ("Canela en polvo", "g", 300, None),
    ("Queso crema", "g", 2000, None),
    ("Pan brioche", "units", 250, None),
    ("Galleta base", "units", 200, None),
    ("Fresa fresca", "g", 3000, None),
    ("Nuez picada", "g", 1500, None),
    ("Chocolate chips", "g", 1800, None),
    ("Tomate cherry", "g", 2500, None),
    ("Albahaca fresca", "g", 800, None),
    ("Harina de avena", "g", 2500, None),
    ("Mantequilla", "g", 5000, None),
    ("Agua tónica", "ml", 4000, None),
    ("Miel", "ml", 1200, None),
]

EXTRA_PRODUCTS: list[dict[str, object]] = [
    {
        "name": "Latte Vainilla",
        "category": "Bebidas Calientes",
        "price": 8200,
        "stock": 150,
        "description": "Latte suave con jarabe de vainilla.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Café molido", 18), ("Leche entera", 180), ("Jarabe de vainilla", 25)],
    },
    {
        "name": "Mocha Caliente",
        "category": "Bebidas Calientes",
        "price": 8800,
        "stock": 140,
        "description": "Café, cacao y leche con espuma.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Café molido", 18), ("Leche entera", 180), ("Cacao en polvo", 10), ("Jarabe de chocolate", 15)],
    },
    {
        "name": "Chai Latte",
        "category": "Bebidas Calientes",
        "price": 8600,
        "stock": 140,
        "description": "Té negro especiado con leche de avena.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Té negro", 5), ("Leche de avena", 180), ("Canela en polvo", 2), ("Jarabe de vainilla", 20)],
    },
    {
        "name": "Chocolate Caliente",
        "category": "Bebidas Calientes",
        "price": 7800,
        "stock": 120,
        "description": "Chocolate espeso con leche entera.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Cacao en polvo", 12), ("Leche entera", 200), ("Miel", 10)],
    },
    {
        "name": "Cold Brew Tonic",
        "category": "Especiales Fríos",
        "price": 9200,
        "stock": 120,
        "description": "Cold brew con agua tónica y limón.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Café molido", 20), ("Agua tónica", 150), ("Hielo", 200), ("Limón", 1)],
    },
    {
        "name": "Latte Frío de Vainilla",
        "category": "Especiales Fríos",
        "price": 9000,
        "stock": 120,
        "description": "Latte helado con vainilla y hielo.",
        "fulfillment": "INGREDIENTS",
        "recipe": [("Café molido", 18), ("Leche de avena", 180), ("Jarabe de vainilla", 25), ("Hielo", 200)],
    },
    {
        "name": "Sándwich Caprese",
        "category": "Sándwiches",
        "price": 11500,
        "stock": 80,
        "description": "Pan brioche con queso crema, tomate y albahaca.",
        "fulfillment": "BOTH",
        "recipe": [("Pan brioche", 2), ("Queso crema", 30), ("Tomate cherry", 60), ("Albahaca fresca", 4)],
    },
    {
        "name": "Brownie con Nuez",
        "category": "Postres Artesanales",
        "price": 9500,
        "stock": 100,
        "description": "Brownie húmedo con nuez y chocolate.",
        "fulfillment": "BOTH",
        "recipe": [("Cacao en polvo", 18), ("Mantequilla", 30), ("Nuez picada", 15), ("Chocolate chips", 10)],
    },
    {
        "name": "Cheesecake de Fresa",
        "category": "Postres Artesanales",
        "price": 10800,
        "stock": 90,
        "description": "Tarta cremosa con base de galleta y fresa.",
        "fulfillment": "BOTH",
        "recipe": [("Queso crema", 80), ("Galleta base", 1), ("Fresa fresca", 60)],
    },
    {
        "name": "Galletas de Avena",
        "category": "Postres Artesanales",
        "price": 6800,
        "stock": 120,
        "description": "Galletas tibias con chocolate chips.",
        "fulfillment": "BOTH",
        "recipe": [("Harina de avena", 50), ("Mantequilla", 20), ("Chocolate chips", 12)],
    },
    {
        "name": "Tostada Brioche",
        "category": "Sándwiches",
        "price": 7200,
        "stock": 120,
        "description": "Tostada caliente con mantequilla y miel.",
        "fulfillment": "BOTH",
        "recipe": [("Pan brioche", 1), ("Mantequilla", 10), ("Miel", 8)],
    },
]

TABLE_ZONES: list[dict[str, object]] = [
    {"name": "Bar Central", "type": "BAR", "floor": 1, "description": "Mesas frente a la barra principal"},
    {"name": "Salón Principal", "type": "FLOOR", "floor": 1, "description": "Área interior principal"},
    {"name": "Terraza Jardín", "type": "OUTDOOR", "floor": 1, "description": "Zona exterior con plantas"},
    {"name": "Salón VIP", "type": "VIP", "floor": 2, "description": "Sala silenciosa para grupos pequeños"},
]

TABLE_LAYOUT: list[tuple[str, int, int, str]] = [
    ("Bar Central", 1, 4, "Mesa bar 1"),
    ("Bar Central", 2, 2, "Mesa bar 2"),
    ("Bar Central", 3, 4, "Mesa bar 3"),
    ("Bar Central", 4, 2, "Mesa bar 4"),
    ("Salón Principal", 5, 4, "Mesa salón 5"),
    ("Salón Principal", 6, 4, "Mesa salón 6"),
    ("Salón Principal", 7, 4, "Mesa salón 7"),
    ("Salón Principal", 8, 4, "Mesa salón 8"),
    ("Salón Principal", 9, 6, "Mesa salón 9"),
    ("Salón Principal", 10, 6, "Mesa salón 10"),
    ("Terraza Jardín", 11, 2, "Mesa terraza 11"),
    ("Terraza Jardín", 12, 4, "Mesa terraza 12"),
    ("Terraza Jardín", 13, 4, "Mesa terraza 13"),
    ("Terraza Jardín", 14, 2, "Mesa terraza 14"),
    ("Salón VIP", 15, 4, "Mesa VIP 15"),
    ("Salón VIP", 16, 4, "Mesa VIP 16"),
]

WORKSHOP_CATEGORY_SPECS: list[tuple[str, str]] = [
    ("Experiencias en Café", "WORKSHOP"),
    ("Arte y Sabores", "WORKSHOP"),
]

WORKSHOP_SPECS: list[dict[str, object]] = [
    {
        "name": "Latte Art Básico",
        "category": "Experiencias en Café",
        "description": "Espuma, textura y práctica de corazones y hojas.",
        "duration_minutes": 120,
        "max_capacity": 12,
        "price": 85000,
        "instructor_name": "Sofía Rincón",
    },
    {
        "name": "Cata Sensorial de Café",
        "category": "Experiencias en Café",
        "description": "Aromas, sabores y métodos de evaluación sensorial.",
        "duration_minutes": 90,
        "max_capacity": 16,
        "price": 72000,
        "instructor_name": "Tomás Vélez",
    },
    {
        "name": "Métodos de Extracción",
        "category": "Experiencias en Café",
        "description": "V60, prensa francesa y aeropress para principiantes.",
        "duration_minutes": 150,
        "max_capacity": 10,
        "price": 98000,
        "instructor_name": "Laura Gómez",
    },
    {
        "name": "Cerámica para Café",
        "category": "Arte y Sabores",
        "description": "Taller de cerámica manual con enfoque en tazas y bowls.",
        "duration_minutes": 180,
        "max_capacity": 8,
        "price": 135000,
        "instructor_name": "Marta Pardo",
    },
    {
        "name": "Maridaje de Postres",
        "category": "Arte y Sabores",
        "description": "Combinaciones de café, bebidas y postres artesanales.",
        "duration_minutes": 100,
        "max_capacity": 14,
        "price": 76000,
        "instructor_name": "Nicolás Peña",
    },
]

WORKSHOP_SCHEDULE_OFFSETS: list[tuple[str, int, int, int, int]] = [
    ("Latte Art Básico", 2, 16, 18, 0),
    ("Latte Art Básico", 9, 16, 18, 0),
    ("Cata Sensorial de Café", 3, 10, 11, 30),
    ("Cata Sensorial de Café", 10, 10, 11, 30),
    ("Métodos de Extracción", 4, 9, 11, 30),
    ("Métodos de Extracción", 11, 9, 11, 30),
    ("Cerámica para Café", 5, 14, 17, 0),
    ("Cerámica para Café", 12, 14, 17, 0),
    ("Maridaje de Postres", 6, 15, 16, 40),
    ("Maridaje de Postres", 13, 15, 16, 40),
]

DEMO_CUSTOMERS: list[dict[str, object]] = [
    {"full_name": "Camila Torres", "email": "camila.torres@demo.local", "phone": "+57 300 111 2201", "points": 120},
    {"full_name": "Andrés Rojas", "email": "andres.rojas@demo.local", "phone": "+57 300 111 2202", "points": 45},
    {"full_name": "Valentina Pérez", "email": "valentina.perez@demo.local", "phone": "+57 300 111 2203", "points": 260},
    {"full_name": "Santiago Gómez", "email": "santiago.gomez@demo.local", "phone": "+57 300 111 2204", "points": 10},
    {"full_name": "Laura Martínez", "email": "laura.martinez@demo.local", "phone": "+57 300 111 2205", "points": 95},
    {"full_name": "Sebastián López", "email": "sebastian.lopez@demo.local", "phone": "+57 300 111 2206", "points": 30},
    {"full_name": "Daniela Sánchez", "email": "daniela.sanchez@demo.local", "phone": "+57 300 111 2207", "points": 180},
    {"full_name": "Paula Ramírez", "email": "paula.ramirez@demo.local", "phone": "+57 300 111 2208", "points": 75},
]

ORDER_SPECS: list[dict[str, object]] = [
    {"customer_email": "camila.torres@demo.local", "table_number": 1, "type": "DINE_IN", "items": [("Espresso", 2), ("Cappuccino", 1)], "status": "PREPARING"},
    {"customer_email": "andres.rojas@demo.local", "table_number": None, "type": "TAKEAWAY", "items": [("Latte Vainilla", 1), ("Brownie con Nuez", 1)], "status": "PENDING"},
    {"customer_email": "valentina.perez@demo.local", "table_number": 5, "type": "DINE_IN", "items": [("Mocha Caliente", 1), ("Cheesecake de Fresa", 1)], "status": "READY"},
    {"customer_email": "santiago.gomez@demo.local", "table_number": 6, "type": "DINE_IN", "items": [("Chai Latte", 2), ("Tostada Brioche", 2)], "status": "DELIVERED"},
    {"customer_email": "laura.martinez@demo.local", "table_number": None, "type": "TAKEAWAY", "items": [("Cold Brew Tonic", 1), ("Sándwich Caprese", 1)], "status": "PENDING"},
    {"customer_email": "sebastian.lopez@demo.local", "table_number": 9, "type": "DINE_IN", "items": [("Latte Frío de Vainilla", 1), ("Galletas de Avena", 2)], "status": "PREPARING"},
    {"customer_email": "daniela.sanchez@demo.local", "table_number": 10, "type": "DINE_IN", "items": [("Chocolate Caliente", 1), ("Tostada Brioche", 1)], "status": "DELIVERED"},
    {"customer_email": "paula.ramirez@demo.local", "table_number": None, "type": "TAKEAWAY", "items": [("Frappé Café", 2), ("Croissant", 1)], "status": "PENDING"},
    {"customer_email": "camila.torres@demo.local", "table_number": 11, "type": "DINE_IN", "items": [("Frappé Matcha", 1), ("Brownie con Nuez", 1)], "status": "READY"},
    {"customer_email": "andres.rojas@demo.local", "table_number": 12, "type": "DINE_IN", "items": [("Limonada de Coco", 2), ("Espresso", 1)], "status": "DELIVERED"},
]


def _slugify(value: str) -> str:
    return value.lower().replace(" ", "-").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")


def _json_permissions(values: Iterable[str]) -> str:
    return json.dumps(sorted(set(values)))


def _get_or_create_role(session: Session, name: str, permissions: Iterable[str]) -> Role:
    role = session.exec(select(Role).where(Role.role_name == name)).first()
    permissions_json = _json_permissions(permissions)
    if not role:
        role = Role(role_name=name, permissions=permissions_json)
        session.add(role)
        session.commit()
        session.refresh(role)
        return role

    if role.permissions != permissions_json:
        role.permissions = permissions_json
        session.add(role)
        session.commit()
        session.refresh(role)
    return role


def _get_or_create_system_user(
    session: Session,
    full_name: str,
    email: str,
    password: str,
    role_name: str,
    phone: str | None = None,
) -> SystemUser:
    user = session.exec(select(SystemUser).where(SystemUser.email == email)).first()
    role = session.exec(select(Role).where(Role.role_name == role_name)).first()
    if not role:
        role = _get_or_create_role(session, role_name, [])

    if not user:
        user = SystemUser(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role_id=role.role_id,
            phone=phone,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    changed = False
    if user.full_name != full_name:
        user.full_name = full_name
        changed = True
    if user.role_id != role.role_id:
        user.role_id = role.role_id
        changed = True
    if phone is not None and user.phone != phone:
        user.phone = phone
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if changed:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _get_or_create_customer(
    session: Session,
    full_name: str,
    email: str,
    phone: str | None = None,
    points: int = 0,
) -> Customer:
    customer = session.exec(select(Customer).where(Customer.email == email)).first()
    if not customer:
        customer = Customer(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=hash_password(CLIENT_PASSWORD),
            is_registered=True,
            loyalty_points=points,
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        return customer

    changed = False
    if customer.full_name != full_name:
        customer.full_name = full_name
        changed = True
    if phone is not None and customer.phone != phone:
        customer.phone = phone
        changed = True
    if not customer.is_registered:
        customer.is_registered = True
        changed = True
    if customer.loyalty_points != points:
        customer.loyalty_points = points
        changed = True
    if not customer.password_hash:
        customer.password_hash = hash_password(CLIENT_PASSWORD)
        changed = True
    if changed:
        session.add(customer)
        session.commit()
        session.refresh(customer)
    return customer


def _get_or_create_category(session: Session, name: str, type_: str) -> Category:
    category = session.exec(select(Category).where(Category.category_name == name)).first()
    if not category:
        category = Category(category_name=name, type=type_)
        session.add(category)
        session.commit()
        session.refresh(category)
        return category

    if category.type != type_:
        category.type = type_
        session.add(category)
        session.commit()
        session.refresh(category)
    return category


def _get_or_create_product(
    session: Session,
    name: str,
    category: Category,
    price: float,
    stock: int,
    description: str,
    fulfillment_type: str,
) -> Product:
    product = session.exec(select(Product).where(Product.name == name)).first()
    if not product:
        product = Product(
            name=name,
            category_id=category.category_id,
            price=price,
            stock_quantity=stock,
            description=description,
            fulfillment_type=fulfillment_type,
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product

    changed = False
    if product.category_id != category.category_id:
        product.category_id = category.category_id
        changed = True
    if float(product.price) != float(price):
        product.price = price
        changed = True
    if product.description != description:
        product.description = description
        changed = True
    if product.fulfillment_type != fulfillment_type:
        product.fulfillment_type = fulfillment_type
        changed = True
    if product.stock_quantity < stock:
        product.stock_quantity = stock
        changed = True
    if changed:
        session.add(product)
        session.commit()
        session.refresh(product)
    return product


def _get_or_create_ingredient(session: Session, name: str, unit: str, min_stock: float, description: str | None) -> Ingredient:
    ingredient = session.exec(select(Ingredient).where(Ingredient.name == name)).first()
    if not ingredient:
        ingredient = Ingredient(name=name, unit=unit, min_stock=min_stock, description=description)
        session.add(ingredient)
        session.commit()
        session.refresh(ingredient)
        return ingredient

    changed = False
    if ingredient.unit != unit:
        ingredient.unit = unit
        changed = True
    if ingredient.min_stock != min_stock:
        ingredient.min_stock = min_stock
        changed = True
    if ingredient.description != description:
        ingredient.description = description
        changed = True
    if changed:
        session.add(ingredient)
        session.commit()
        session.refresh(ingredient)
    return ingredient


def _ensure_product_inbound(session: Session, admin_id: int, product: Product) -> None:
    if not product.stock_quantity or product.stock_quantity <= 0:
        return
    existing = session.exec(
        select(InventoryMovement)
        .where(InventoryMovement.product_id == product.product_id)
        .where(InventoryMovement.notes == f"{SEED_PREFIX} product stock")
    ).first()
    if existing:
        return
    session.add(
        InventoryMovement(
            product_id=product.product_id,
            system_user_id=admin_id,
            movement_type="IN",
            quantity=product.stock_quantity,
            notes=f"{SEED_PREFIX} product stock",
        )
    )
    session.commit()


def _ensure_ingredient_inbound(session: Session, admin_id: int, ingredient: Ingredient, quantity: float) -> None:
    if quantity <= 0:
        return
    existing = session.exec(
        select(IngredientStockMovement)
        .where(IngredientStockMovement.ingredient_id == ingredient.ingredient_id)
        .where(IngredientStockMovement.notes == f"{SEED_PREFIX} ingredient stock")
    ).first()
    if existing:
        return
    session.add(
        IngredientStockMovement(
            ingredient_id=ingredient.ingredient_id,
            system_user_id=admin_id,
            movement_type="IN",
            quantity=quantity,
            notes=f"{SEED_PREFIX} ingredient stock",
        )
    )
    session.commit()


def _ensure_consumption(session: Session, product: Product, ingredient: Ingredient, quantity_used: float) -> None:
    existing = session.exec(
        select(ProductConsumption).where(
            ProductConsumption.product_id == product.product_id,
            ProductConsumption.ingredient_id == ingredient.ingredient_id,
        )
    ).first()
    if existing:
        if float(existing.quantity_used) != float(quantity_used):
            existing.quantity_used = quantity_used
            session.add(existing)
            session.commit()
        return
    session.add(ProductConsumption(product_id=product.product_id, ingredient_id=ingredient.ingredient_id, quantity_used=quantity_used))
    session.commit()


def _get_or_create_zone(session: Session, name: str, type_: str, floor: int, description: str | None) -> TableZone:
    zone = session.exec(select(TableZone).where(TableZone.zone_name == name)).first()
    if not zone:
        zone = TableZone(zone_name=name, zone_type=type_, floor_number=floor, description=description)
        session.add(zone)
        session.commit()
        session.refresh(zone)
        return zone

    changed = False
    if zone.zone_type != type_:
        zone.zone_type = type_
        changed = True
    if zone.floor_number != floor:
        zone.floor_number = floor
        changed = True
    if zone.description != description:
        zone.description = description
        changed = True
    if changed:
        session.add(zone)
        session.commit()
        session.refresh(zone)
    return zone


def _get_or_create_table(
    session: Session,
    zone: TableZone,
    table_number: int,
    capacity: int,
    label: str,
    status: str = "FREE",
) -> TableSpot:
    table_code = f"TBL-{table_number:02d}"
    table = session.exec(select(TableSpot).where(TableSpot.table_code == table_code)).first()
    if not table:
        table = TableSpot(zone_id=zone.zone_id, table_number=table_number, table_code=table_code, capacity=capacity, status=status, label=label, is_active=True, qr_code_url=f"https://coffee-and-chill.local/menu/{table_code}")
        session.add(table)
        session.commit()
        session.refresh(table)
        return table

    changed = False
    if table.zone_id != zone.zone_id:
        table.zone_id = zone.zone_id
        changed = True
    if table.capacity != capacity:
        table.capacity = capacity
        changed = True
    if table.label != label:
        table.label = label
        changed = True
    if table.status != status:
        table.status = status
        changed = True
    if table.is_active is not True:
        table.is_active = True
        changed = True
    if not table.qr_code_url:
        table.qr_code_url = f"https://coffee-and-chill.local/menu/{table_code}"
        changed = True
    if changed:
        session.add(table)
        session.commit()
        session.refresh(table)
    return table


def _get_or_create_workshop(session: Session, category: Category, spec: dict[str, object]) -> Workshop:
    workshop = session.exec(select(Workshop).where(Workshop.name == spec["name"])).first()
    if not workshop:
        workshop = Workshop(
            name=str(spec["name"]),
            category_id=category.category_id,
            description=str(spec["description"]),
            duration_minutes=int(spec["duration_minutes"]),
            max_capacity=int(spec["max_capacity"]),
            price=float(spec["price"]),
            instructor_name=str(spec["instructor_name"]),
            is_active=True,
        )
        session.add(workshop)
        session.commit()
        session.refresh(workshop)
        return workshop

    changed = False
    if workshop.category_id != category.category_id:
        workshop.category_id = category.category_id
        changed = True
    if workshop.description != spec["description"]:
        workshop.description = str(spec["description"])
        changed = True
    if workshop.duration_minutes != int(spec["duration_minutes"]):
        workshop.duration_minutes = int(spec["duration_minutes"])
        changed = True
    if workshop.max_capacity != int(spec["max_capacity"]):
        workshop.max_capacity = int(spec["max_capacity"])
        changed = True
    if float(workshop.price) != float(spec["price"]):
        workshop.price = float(spec["price"])
        changed = True
    if workshop.instructor_name != spec["instructor_name"]:
        workshop.instructor_name = str(spec["instructor_name"])
        changed = True
    if not workshop.is_active:
        workshop.is_active = True
        changed = True
    if changed:
        session.add(workshop)
        session.commit()
        session.refresh(workshop)
    return workshop


def _get_or_create_schedule(
    session: Session,
    workshop: Workshop,
    schedule_date: date,
    start: time,
    end: time,
    available_slots: int,
) -> WorkshopSchedule:
    schedule = session.exec(
        select(WorkshopSchedule).where(
            WorkshopSchedule.workshop_id == workshop.workshop_id,
            WorkshopSchedule.schedule_date == schedule_date,
            WorkshopSchedule.start_time == start,
        )
    ).first()
    if not schedule:
        schedule = WorkshopSchedule(
            workshop_id=workshop.workshop_id,
            schedule_date=schedule_date,
            start_time=start,
            end_time=end,
            available_slots=available_slots,
            status="OPEN",
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        return schedule

    changed = False
    if schedule.end_time != end:
        schedule.end_time = end
        changed = True
    if schedule.available_slots != available_slots:
        schedule.available_slots = available_slots
        changed = True
    if schedule.status == "FULL" and available_slots > 0:
        schedule.status = "OPEN"
        changed = True
    if changed:
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
    return schedule


def _get_or_create_reservation(
    session: Session,
    customer: Customer,
    schedule: WorkshopSchedule,
    admin_id: int,
    slots: int,
    special_requests: str,
) -> WorkshopReservation:
    existing = session.exec(
        select(WorkshopReservation).where(
            WorkshopReservation.customer_id == customer.customer_id,
            WorkshopReservation.schedule_id == schedule.schedule_id,
            WorkshopReservation.quantity_slots == slots,
        )
    ).first()
    if existing:
        return existing

    if schedule.available_slots < slots:
        slots = max(1, schedule.available_slots)

    reservation = WorkshopReservation(
        customer_id=customer.customer_id,
        schedule_id=schedule.schedule_id,
        system_user_id=admin_id,
        quantity_slots=slots,
        total_price=None,
        status="CONFIRMED",
        special_requests=special_requests,
    )
    workshop = session.get(Workshop, schedule.workshop_id)
    reservation.total_price = float(workshop.price) * slots if workshop else None
    schedule.available_slots -= slots
    if schedule.available_slots <= 0:
        schedule.available_slots = 0
        schedule.status = "FULL"

    session.add(reservation)
    session.add(schedule)
    session.commit()
    session.refresh(reservation)
    return reservation


def _seed_roles_and_users(session: Session) -> tuple[SystemUser, list[SystemUser]]:
    admin_role = _get_or_create_role(session, "admin", ROLE_PERMISSIONS["admin"])
    _get_or_create_role(session, "manager", ROLE_PERMISSIONS["manager"])
    _get_or_create_role(session, "cashier", ROLE_PERMISSIONS["cashier"])
    _get_or_create_role(session, "waiter", ROLE_PERMISSIONS["waiter"])
    _get_or_create_role(session, "kitchen", ROLE_PERMISSIONS["kitchen"])

    admin = _get_or_create_system_user(session, "Admin Demo", ADMIN_EMAIL, ADMIN_PASSWORD, "admin", "+57 300 100 0001")
    _get_or_create_system_user(session, "Margarita León", "manager@demo.local", "manager123", "manager", "+57 300 100 0002")
    _get_or_create_system_user(session, "Laura Cashier", "cashier@demo.local", "cashier123", "cashier", "+57 300 100 0003")
    waiter = _get_or_create_system_user(session, "Pedro Mesa", "waiter@demo.local", "waiter123", "waiter", "+57 300 100 0004")
    _get_or_create_system_user(session, "Javier Cocina", "kitchen@demo.local", "kitchen123", "kitchen", "+57 300 100 0005")

    return admin, [admin, waiter]


def _seed_customers(session: Session) -> list[Customer]:
    customers = []
    for spec in DEMO_CUSTOMERS:
        customer = _get_or_create_customer(
            session,
            full_name=str(spec["full_name"]),
            email=str(spec["email"]),
            phone=str(spec["phone"]),
            points=int(spec["points"]),
        )
        customers.append(customer)

    legacy_customer = _get_or_create_customer(session, "Cliente Demo", CLIENT_EMAIL, "+57 300 100 0099", 0)
    if legacy_customer not in customers:
        customers.insert(0, legacy_customer)

    return customers


def _seed_catalog(session: Session, admin_id: int) -> tuple[dict[str, Product], dict[str, Ingredient]]:
    from .catalog import seed_catalog_and_inventory

    seed_catalog_and_inventory(session, admin_id)

    categories: dict[str, Category] = {}
    for name, type_ in EXTRA_PRODUCT_CATEGORIES:
        categories[name] = _get_or_create_category(session, name, type_)

    all_products: dict[str, Product] = {
        p.name: p for p in session.exec(select(Product)).all()
    }
    all_ingredients: dict[str, Ingredient] = {
        i.name: i for i in session.exec(select(Ingredient)).all()
    }

    for name, unit, min_stock, description in EXTRA_INGREDIENTS:
        ingredient = _get_or_create_ingredient(session, name, unit, min_stock, description)
        all_ingredients[name] = ingredient
        _ensure_ingredient_inbound(session, admin_id, ingredient, max(float(min_stock) * 4, 2500))

    for spec in EXTRA_PRODUCTS:
        category = _get_or_create_category(session, str(spec["category"]), "PRODUCT")
        product = _get_or_create_product(
            session,
            name=str(spec["name"]),
            category=category,
            price=float(spec["price"]),
            stock=int(spec["stock"]),
            description=str(spec["description"]),
            fulfillment_type=str(spec["fulfillment"]),
        )
        all_products[product.name] = product
        _ensure_product_inbound(session, admin_id, product)

        for ing_name, qty in spec["recipe"]:
            ingredient = all_ingredients.get(str(ing_name))
            if not ingredient:
                raise RuntimeError(f"Ingrediente faltante para receta demo: {ing_name}")
            _ensure_consumption(session, product, ingredient, float(qty))

    return all_products, all_ingredients


def _seed_zones_and_tables(session: Session) -> dict[int, TableSpot]:
    zones: dict[str, TableZone] = {}
    for spec in TABLE_ZONES:
        zones[str(spec["name"])] = _get_or_create_zone(
            session,
            name=str(spec["name"]),
            type_=str(spec["type"]),
            floor=int(spec["floor"]),
            description=str(spec["description"]),
        )

    tables_by_number: dict[int, TableSpot] = {}
    for zone_name, table_number, capacity, label in TABLE_LAYOUT:
        status = "FREE"
        if table_number == 14:
            status = "MAINTENANCE"
        elif table_number == 15:
            status = "RESERVED"
        tables_by_number[table_number] = _get_or_create_table(
            session,
            zone=zones[zone_name],
            table_number=table_number,
            capacity=capacity,
            label=label,
            status=status,
        )
    return tables_by_number


def _seed_workshops(session: Session) -> tuple[dict[str, Workshop], dict[str, WorkshopSchedule]]:
    workshop_categories: dict[str, Category] = {}
    for name, type_ in WORKSHOP_CATEGORY_SPECS:
        workshop_categories[name] = _get_or_create_category(session, name, type_)

    workshops: dict[str, Workshop] = {}
    for spec in WORKSHOP_SPECS:
        category = workshop_categories[str(spec["category"])]
        workshop = _get_or_create_workshop(session, category, spec)
        workshops[workshop.name] = workshop

    schedules: dict[str, WorkshopSchedule] = {}
    today = date.today()
    for workshop_name, day_offset, start_hour, end_hour, end_minute in WORKSHOP_SCHEDULE_OFFSETS:
        workshop = workshops[workshop_name]
        schedule = _get_or_create_schedule(
            session,
            workshop=workshop,
            schedule_date=today + timedelta(days=day_offset),
            start=time(start_hour, 0),
            end=time(end_hour, end_minute),
            available_slots=workshop.max_capacity,
        )
        schedules[f"{workshop_name}:{day_offset}:{start_hour}"] = schedule

    return workshops, schedules


def _seed_workshop_reservations(
    session: Session,
    admin_id: int,
    customers: list[Customer],
    workshops: dict[str, Workshop],
    schedules: dict[str, WorkshopSchedule],
) -> list[WorkshopReservation]:
    target_specs = [
        ("Latte Art Básico:2:16", "camila.torres@demo.local", 2, "Grupo creativo de amigos"),
        ("Cata Sensorial de Café:3:10", "andres.rojas@demo.local", 3, "Cumpleaños con cata"),
        ("Métodos de Extracción:4:9", "valentina.perez@demo.local", 1, "Quiero aprender V60"),
        ("Cerámica para Café:5:14", "santiago.gomez@demo.local", 2, "Actividad de fin de semana"),
        ("Maridaje de Postres:6:15", "laura.martinez@demo.local", 4, "Salida corporativa"),
        ("Latte Art Básico:9:16", "sebastian.lopez@demo.local", 1, "Regalo sorpresa"),
    ]

    customer_by_email = {c.email: c for c in customers if c.email}
    reservations: list[WorkshopReservation] = []
    for schedule_key, email, slots, note in target_specs:
        schedule = schedules[schedule_key]
        customer = customer_by_email[email]
        reservation = _get_or_create_reservation(session, customer, schedule, admin_id, slots, note)
        reservations.append(reservation)
    return reservations


def _build_order_carts() -> list[dict[str, object]]:
    return ORDER_SPECS


def _apply_order_status(session: Session, order: Order, status: str) -> None:
    order.status = status
    if status == "DELIVERED" and order.table_id:
        table = session.get(TableSpot, order.table_id)
        if table:
            table.status = "FREE"
            session.add(table)
    elif status in {"PREPARING", "READY"} and order.table_id:
        table = session.get(TableSpot, order.table_id)
        if table:
            table.status = "OCCUPIED"
            session.add(table)
    session.add(order)
    session.commit()
    session.refresh(order)


def _seed_orders_payments_and_logs(
    session: Session,
    admin: SystemUser,
    customers: list[Customer],
    tables_by_number: dict[int, TableSpot],
    products_by_name: dict[str, Product],
) -> None:
    customer_by_email = {c.email: c for c in customers if c.email}
    existing_notes = {
        note
        for note in session.exec(select(Order.notes).where(Order.notes.like(f"{SEED_PREFIX}%"))).all()
        if note
    }

    for index, spec in enumerate(_build_order_carts(), start=1):
        note = f"{SEED_PREFIX} order {index:02d}"
        if note in existing_notes:
            continue

        customer = customer_by_email[str(spec["customer_email"])]
        table_number = spec["table_number"]
        table_id = tables_by_number[int(table_number)].table_id if table_number else None
        cart_items = [OrderItemCreate(product_id=products_by_name[name].product_id, quantity=quantity, special_instructions=None) for name, quantity in spec["items"]]

        checkout = CheckoutRequest(
            order_type=str(spec["type"]),
            table_id=table_id,
            notes=note,
            items=cart_items,
        )
        current_user = UserResponse(id=customer.customer_id, name=customer.full_name, email=customer.email or "", role="client")
        order = process_checkout(session, checkout, current_user)
        _apply_order_status(session, order, str(spec["status"]))

        payment_method = ["CASH", "CARD", "TRANSFER", "WALLET"][index % 4]
        payment_status = "COMPLETED" if str(spec["status"]) in {"READY", "DELIVERED"} else "PENDING"
        payment = session.exec(select(Payment).where(Payment.order_id == order.order_id)).first()
        if not payment:
            payment = Payment(
                order_id=order.order_id,
                customer_id=customer.customer_id,
                payment_method=payment_method,
                amount=order.total_amount,
                status=payment_status,
                transaction_reference=f"{SEED_PREFIX}-PAY-{index:04d}",
                tip_amount=500 if payment_status == "COMPLETED" else 0,
                system_user_id=admin.system_user_id,
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
        else:
            payment.payment_method = payment_method
            payment.amount = order.total_amount
            payment.status = payment_status
            payment.transaction_reference = f"{SEED_PREFIX}-PAY-{index:04d}"
            payment.tip_amount = 500 if payment_status == "COMPLETED" else 0
            payment.system_user_id = admin.system_user_id
            session.add(payment)
            session.commit()
            session.refresh(payment)

        if payment_status == "COMPLETED":
            invoice_number = f"INV-2026-{index:04d}"
            invoice = session.exec(select(Invoice).where(Invoice.invoice_number == invoice_number)).first()
            if not invoice:
                invoice = Invoice(
                    order_id=order.order_id,
                    customer_id=customer.customer_id,
                    payment_id=payment.payment_id,
                    invoice_type="TICKET",
                    invoice_number=invoice_number,
                    tax_id="900123456",
                    total_amount=order.total_amount + payment.tip_amount,
                    pdf_url=f"https://coffee-and-chill.local/invoices/{invoice_number}.pdf",
                )
                session.add(invoice)
                session.commit()

        notification_type = "ORDER_STATUS"
        message = f"Tu pedido {order.order_id} quedó en estado {order.status}."
        notification = session.exec(
            select(Notification).where(
                Notification.customer_id == customer.customer_id,
                Notification.related_order_id == order.order_id,
                Notification.notification_type == notification_type,
            )
        ).first()
        if not notification:
            notification = Notification(
                customer_id=customer.customer_id,
                related_order_id=order.order_id,
                notification_type=notification_type,
                message=message,
                channel="PUSH",
                status="SENT" if payment_status == "COMPLETED" else "PENDING",
            )
            session.add(notification)
            session.commit()

        activity = session.exec(
            select(ActivityLog).where(
                ActivityLog.customer_id == customer.customer_id,
                ActivityLog.related_order_id == order.order_id,
                ActivityLog.activity_type == "ORDER_SEEDED",
            )
        ).first()
        if not activity:
            activity = ActivityLog(
                customer_id=customer.customer_id,
                activity_type="ORDER_SEEDED",
                related_order_id=order.order_id,
                related_payment_id=payment.payment_id if payment else None,
                activity_metadata={
                    "seed": SEED_PREFIX,
                    "order_status": order.status,
                    "payment_status": payment_status,
                    "note": note,
                },
            )
            session.add(activity)
            session.commit()


def run_full_demo() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        admin, _staff = _seed_roles_and_users(session)
        customers = _seed_customers(session)
        products_by_name, _ingredients_by_name = _seed_catalog(session, admin.system_user_id)
        tables_by_number = _seed_zones_and_tables(session)
        workshops, schedules = _seed_workshops(session)
        _seed_workshop_reservations(session, admin.system_user_id, customers, workshops, schedules)
        _seed_orders_payments_and_logs(session, admin, customers, tables_by_number, products_by_name)

    print("Seed demo completo aplicado.")


if __name__ == "__main__":
    run_full_demo()