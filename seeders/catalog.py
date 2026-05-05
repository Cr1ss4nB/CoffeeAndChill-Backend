"""Seeder: categorías, productos, insumos, recetas (consumo) y movimientos iniciales."""

from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.inventory import (
    Ingredient,
    IngredientStockMovement,
    InventoryMovement,
    ProductConsumption,
)

# Nombres del demo (para comprobar idempotencia y get-or-create)
CATEGORY_DEMO: list[tuple[str, str]] = [
    ("Bebidas Calientes", "PRODUCT"),
    ("Bebidas Frías", "PRODUCT"),
    ("Pasabocas", "PRODUCT"),
    ("Cerámica", "WORKSHOP"),
]

PRODUCT_SPECS: list[tuple[str, str, float, int, str]] = [
    # (nombre, clave de categoría por nombre, precio, stock, descripción)
    ("Espresso", "Bebidas Calientes", 4500, 200, "Espresso doble de café de especialidad"),
    ("Cappuccino", "Bebidas Calientes", 6500, 200, "Espresso con leche vaporizada y espuma"),
    ("Latte", "Bebidas Calientes", 7000, 200, "Espresso con leche cremosa vaporizada"),
    ("Americano", "Bebidas Calientes", 5000, 200, "Espresso con agua caliente"),
    ("Frappé Café", "Bebidas Frías", 9500, 200, "Café frío con hielo, leche y jarabe"),
    ("Frappé Matcha", "Bebidas Frías", 10000, 200, "Matcha frío con hielo y leche"),
    ("Limonada de Coco", "Bebidas Frías", 8000, 200, "Limonada refrescante con leche de coco"),
    ("Croissant", "Pasabocas", 5500, 30, "Croissant artesanal de mantequilla"),
    ("Muffin de Arándanos", "Pasabocas", 6000, 20, "Muffin casero con arándanos frescos"),
]

INGREDIENT_SPECS: list[tuple[str, str, float, str | None]] = [
    ("Café molido", "g", 500, "Café de especialidad molido medio"),
    ("Leche entera", "ml", 3000, None),
    ("Leche de coco", "ml", 500, None),
    ("Jarabe de azúcar", "ml", 500, None),
    ("Hielo", "g", 2000, None),
    ("Matcha en polvo", "g", 200, None),
    ("Agua caliente", "ml", 0, None),
    ("Limón", "units", 10, None),
]

# Stock inicial de insumos: nombre -> cantidad (0 = sin movimiento IN)
INITIAL_INGREDIENT_STOCK: dict[str, float] = {
    "Café molido": 2000,
    "Leche entera": 10000,
    "Leche de coco": 2000,
    "Jarabe de azúcar": 2000,
    "Hielo": 10000,
    "Matcha en polvo": 500,
    "Agua caliente": 0,
    "Limón": 30,
}

# (producto, insumo, cantidad por unidad vendida)
CONSUMPTION_SPECS: list[tuple[str, str, float]] = [
    ("Espresso", "Café molido", 18),
    ("Cappuccino", "Café molido", 18),
    ("Cappuccino", "Leche entera", 120),
    ("Latte", "Café molido", 18),
    ("Latte", "Leche entera", 180),
    ("Americano", "Café molido", 18),
    ("Americano", "Agua caliente", 120),
    ("Frappé Café", "Café molido", 18),
    ("Frappé Café", "Leche entera", 150),
    ("Frappé Café", "Hielo", 200),
    ("Frappé Café", "Jarabe de azúcar", 30),
    ("Frappé Matcha", "Matcha en polvo", 8),
    ("Frappé Matcha", "Leche entera", 150),
    ("Frappé Matcha", "Hielo", 200),
    ("Frappé Matcha", "Jarabe de azúcar", 20),
    ("Limonada de Coco", "Limón", 2),
    ("Limonada de Coco", "Leche de coco", 150),
    ("Limonada de Coco", "Hielo", 200),
    ("Limonada de Coco", "Jarabe de azúcar", 30),
]

_SEED_NOTE = "Stock inicial (seed)"


def _get_or_create_category(session: Session, name: str, type_: str) -> Category:
    c = session.exec(select(Category).where(Category.category_name == name)).first()
    if c:
        return c
    c = Category(category_name=name, type=type_)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


# Bebidas con receta: cupo = insumos; pasabocas sin receta: solo unidades de producto
_PRODUCT_FULFILLMENT: dict[str, str] = {
    **{n: "INGREDIENTS" for n in ("Espresso", "Cappuccino", "Latte", "Americano", "Frappé Café", "Frappé Matcha", "Limonada de Coco")},
    "Croissant": "STOCK",
    "Muffin de Arándanos": "STOCK",
}


def _get_or_create_product(
    session: Session,
    name: str,
    category: Category,
    price: float,
    stock: int,
    description: str,
) -> Product:
    p = session.exec(select(Product).where(Product.name == name)).first()
    if p:
        return p
    p = Product(
        name=name,
        category_id=category.category_id,
        price=price,
        stock_quantity=stock,
        description=description,
        fulfillment_type=_PRODUCT_FULFILLMENT.get(name, "STOCK"),
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def _ensure_product_initial_in(session: Session, admin_id: int, product: Product) -> None:
    if not product.stock_quantity or product.stock_quantity <= 0:
        return
    existing = session.exec(
        select(InventoryMovement)
        .where(InventoryMovement.product_id == product.product_id)
        .where(InventoryMovement.notes == _SEED_NOTE)
    ).first()
    if existing:
        return
    session.add(
        InventoryMovement(
            product_id=product.product_id,
            system_user_id=admin_id,
            movement_type="IN",
            quantity=product.stock_quantity,
            notes=_SEED_NOTE,
        )
    )
    session.commit()


def _get_or_create_ingredient(
    session: Session, name: str, unit: str, min_stock: float, description: str | None
) -> Ingredient:
    i = session.exec(select(Ingredient).where(Ingredient.name == name)).first()
    if i:
        return i
    i = Ingredient(name=name, unit=unit, min_stock=min_stock, description=description)
    session.add(i)
    session.commit()
    session.refresh(i)
    return i


def _ensure_ingredient_initial_in(session: Session, admin_id: int, ingredient: Ingredient, qty: float) -> None:
    if qty <= 0:
        return
    existing = session.exec(
        select(IngredientStockMovement)
        .where(IngredientStockMovement.ingredient_id == ingredient.ingredient_id)
        .where(IngredientStockMovement.notes == _SEED_NOTE)
    ).first()
    if existing:
        return
    session.add(
        IngredientStockMovement(
            ingredient_id=ingredient.ingredient_id,
            system_user_id=admin_id,
            movement_type="IN",
            quantity=qty,
            notes=_SEED_NOTE,
        )
    )
    session.commit()


def _ensure_consumption(
    session: Session, product: Product, ingredient: Ingredient, quantity_used: float
) -> None:
    existing = session.exec(
        select(ProductConsumption).where(
            ProductConsumption.product_id == product.product_id,
            ProductConsumption.ingredient_id == ingredient.ingredient_id,
        )
    ).first()
    if existing:
        return
    session.add(
        ProductConsumption(
            product_id=product.product_id, ingredient_id=ingredient.ingredient_id, quantity_used=quantity_used
        )
    )
    session.commit()


def seed_catalog_and_inventory(session: Session, admin_id: int) -> None:
    """
    Crea o completa el catálogo demo (categorías, productos, insumos, recetas, movimientos).
    Idempotente: puede ejecutarse varias veces; no duplica filas lógicamente
    (comprueba por nombres y notas de seed).
    """
    print("Asegurando categorías de demo...")
    by_cat_name: dict[str, Category] = {}
    for name, ctype in CATEGORY_DEMO:
        c = _get_or_create_category(session, name, ctype)
        by_cat_name[name] = c

    print("Asegurando productos de demo...")
    products_by_name: dict[str, Product] = {}
    for name, cat_name, price, stock, desc in PRODUCT_SPECS:
        cat = by_cat_name[cat_name]
        p = _get_or_create_product(session, name, cat, price, stock, desc)
        products_by_name[name] = p
        _ensure_product_initial_in(session, admin_id, p)

    print("Asegurando insumos y stock inicial...")
    ingredients_by_name: dict[str, Ingredient] = {}
    for name, unit, min_s, desc in INGREDIENT_SPECS:
        ing = _get_or_create_ingredient(session, name, unit, min_s, desc)
        ingredients_by_name[name] = ing
        qty = INITIAL_INGREDIENT_STOCK.get(name, 0)
        _ensure_ingredient_initial_in(session, admin_id, ing, qty)

    print("Asegurando recetas (consumo por producto)...")
    for prod_name, ing_name, qused in CONSUMPTION_SPECS:
        p = products_by_name[prod_name]
        ing = ingredients_by_name[ing_name]
        _ensure_consumption(session, p, ing, qused)

    print("Catálogo e inventario demo listos.")
