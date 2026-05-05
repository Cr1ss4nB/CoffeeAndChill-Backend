"""
Disponibilidad de venta: misma regla para catálogo, inventario y checkout.
Cupo por producto = `Product.stock_quantity` (límite lógico del backend).
Cupo por receta = min_i floor(stock_ing / quantity_used) con insumos activos.
"""

from __future__ import annotations

import math
from typing import Optional

from sqlmodel import Session, func, select, case

from app.core.fulfillment import FulfillmentType, resolve_effective_fulfillment
from app.models.catalog import Product
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption


def get_ingredient_current_stock(session: Session, ingredient_id: int) -> float:
    result = session.exec(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (IngredientStockMovement.movement_type == "IN", IngredientStockMovement.quantity),
                        (
                            IngredientStockMovement.movement_type.in_(["OUT", "SALE", "WASTE"]),
                            -IngredientStockMovement.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(IngredientStockMovement.ingredient_id == ingredient_id)
    ).one()
    return float(result)


def max_sellable_units_by_recipe(session: Session, product_id: int) -> Optional[int]:
    """
    None si el producto no tiene líneas de consumo.
    0 si falta un insumo activo o la receta es inválida o insuficiente.
    """
    consumptions = session.exec(
        select(ProductConsumption).where(ProductConsumption.product_id == product_id)
    ).all()
    if not consumptions:
        return None

    limits: list[int] = []
    for c in consumptions:
        if c.quantity_used <= 0:
            return 0
        ing = session.get(Ingredient, c.ingredient_id)
        if not ing or not ing.is_active:
            return 0
        stock = get_ingredient_current_stock(session, c.ingredient_id)
        n = int(math.floor(stock / c.quantity_used))
        limits.append(n)
    if not limits:
        return 0
    return min(limits)


def get_product_cupo_by_stock_field(product: Product) -> int:
    """Cupo derivado de `Product.stock_quantity` (lo que el checkout actualiza)."""
    return max(0, int(product.stock_quantity or 0))


def compute_sellable_snapshot(session: Session, product: Product) -> dict:
    """
    Misma lógica para listados y carrito: no contradecir "agotado" por stock
    si la política es solo receta y aún hay insumos.
    """
    recipe_max = max_sellable_units_by_recipe(session, product.product_id)
    has_recipe = recipe_max is not None
    if recipe_max is None:
        effective = FulfillmentType.STOCK.value
    else:
        effective = resolve_effective_fulfillment(product.fulfillment_type, True)

    stock_cupo = get_product_cupo_by_stock_field(product)
    if not has_recipe:
        ats = stock_cupo
        ingredient_limited = False
    elif effective == FulfillmentType.INGREDIENTS.value:
        ats = recipe_max
        ingredient_limited = True
    elif effective == FulfillmentType.BOTH.value:
        ats = min(stock_cupo, recipe_max)
        ingredient_limited = recipe_max < stock_cupo
    else:
        ats = stock_cupo
        ingredient_limited = False

    return {
        "available_to_sell": max(0, ats),
        "max_units_by_ingredients": recipe_max,
        "max_units_by_product_stock": stock_cupo,
        "ingredient_limited": has_recipe and bool(ingredient_limited),
        "fulfillment_type": product.fulfillment_type,
    }


def can_sell_quantity(
    session: Session,
    product: Product,
    quantity: int,
) -> bool:
    if quantity <= 0:
        return False
    snap = compute_sellable_snapshot(session, product)
    return quantity <= snap["available_to_sell"]


def validate_recipe_allows_ingredient_deduction(
    session: Session, product: Product, quantity: int
) -> tuple[bool, str]:
    """
    Comprueba que la suma de insumos requerida no supere el stock,
    dado un número de unidades a vender. Si no hay receta, ok.
    """
    if quantity <= 0:
        return False, "Cantidad inválida"
    consumptions = session.exec(
        select(ProductConsumption).where(ProductConsumption.product_id == product.product_id)
    ).all()
    if not consumptions:
        return True, ""
    for c in consumptions:
        if c.quantity_used <= 0:
            return False, "Línea de receta con quantity_used inválido"
        ing = session.get(Ingredient, c.ingredient_id)
        if not ing:
            return False, f"Insumo faltante en receta (id {c.ingredient_id})"
        if not ing.is_active:
            return False, f"Insumo inactivo: {ing.name}"
        need = c.quantity_used * quantity
        current = get_ingredient_current_stock(session, c.ingredient_id)
        if current + 1e-9 < need:
            return (
                False,
                f"Stock insuficiente de {ing.name}. Necesario: {need} {ing.unit}, disponible: {current:.2f} {ing.unit}.",
            )
    return True, ""


def should_decrement_product_stock(fulfillment_type: str, has_recipe: bool) -> bool:
    if not has_recipe:
        return True
    eff = resolve_effective_fulfillment(fulfillment_type, has_recipe)
    if eff == FulfillmentType.INGREDIENTS.value:
        return False
    return True


def should_record_product_inventory_movement(fulfillment_type: str, has_recipe: bool) -> bool:
    if not has_recipe:
        return True
    eff = resolve_effective_fulfillment(fulfillment_type, has_recipe)
    if eff == FulfillmentType.INGREDIENTS.value:
        return False
    return True