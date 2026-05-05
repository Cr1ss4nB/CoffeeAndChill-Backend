"""Cómo se calcula la venta y el límite de unidades: stock de producto, insumos, o el mínimo de ambos."""

from enum import Enum


class FulfillmentType(str, Enum):
    """Política de stock vs receta (product_consumption)."""

    # Solo conteo/ajuste vía `Product.stock_quantity` e inventario de producto.
    STOCK = "STOCK"
    # La venta la limita solo la receta; `stock_quantity` no afecta visibilidad ni cupo.
    INGREDIENTS = "INGREDIENTS"
    # Mínimo entre cupo de producto y de insumos (nunca más unidades que el más restrictivo).
    BOTH = "BOTH"


def resolve_effective_fulfillment(fulfillment_type: str, has_recipe: bool) -> str:
    """
    Con receta, STOCK deja de ser coherente (la venta sigue descontando insumos);
    se trata como BOTH para cálculo de cupo. Sin receta, solo STOCK aplica.
    """
    if not has_recipe:
        return FulfillmentType.STOCK.value
    if fulfillment_type == FulfillmentType.STOCK.value and has_recipe:
        return FulfillmentType.BOTH.value
    return fulfillment_type
