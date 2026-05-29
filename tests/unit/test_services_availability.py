"""Unit tests for pure functions in app/services/availability.py — no DB or HTTP client imports."""
from unittest.mock import MagicMock

import pytest

from app.core.fulfillment import FulfillmentType
from app.services.availability import (
    get_product_cupo_by_stock_field,
    should_decrement_product_stock,
    should_record_product_inventory_movement,
)

# ---------------------------------------------------------------------------
# should_decrement_product_stock
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ft", [
    FulfillmentType.STOCK.value,
    FulfillmentType.INGREDIENTS.value,
    FulfillmentType.BOTH.value,
])
def test_should_decrement_stock_no_recipe_always_true(ft):
    assert should_decrement_product_stock(ft, False) is True


def test_should_decrement_stock_ingredients_with_recipe_false():
    assert should_decrement_product_stock(FulfillmentType.INGREDIENTS.value, True) is False


def test_should_decrement_stock_stock_with_recipe_true():
    assert should_decrement_product_stock(FulfillmentType.STOCK.value, True) is True


def test_should_decrement_stock_both_with_recipe_true():
    assert should_decrement_product_stock(FulfillmentType.BOTH.value, True) is True


# ---------------------------------------------------------------------------
# should_record_product_inventory_movement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ft", [
    FulfillmentType.STOCK.value,
    FulfillmentType.INGREDIENTS.value,
    FulfillmentType.BOTH.value,
])
def test_should_record_movement_no_recipe_always_true(ft):
    assert should_record_product_inventory_movement(ft, False) is True


def test_should_record_movement_ingredients_with_recipe_false():
    assert should_record_product_inventory_movement(FulfillmentType.INGREDIENTS.value, True) is False


def test_should_record_movement_stock_with_recipe_true():
    assert should_record_product_inventory_movement(FulfillmentType.STOCK.value, True) is True


def test_should_record_movement_both_with_recipe_true():
    assert should_record_product_inventory_movement(FulfillmentType.BOTH.value, True) is True


# ---------------------------------------------------------------------------
# get_product_cupo_by_stock_field
# ---------------------------------------------------------------------------

def _product(stock_quantity):
    p = MagicMock()
    p.stock_quantity = stock_quantity
    return p


def test_cupo_positive_stock():
    assert get_product_cupo_by_stock_field(_product(10)) == 10


def test_cupo_zero_stock():
    assert get_product_cupo_by_stock_field(_product(0)) == 0


def test_cupo_none_stock():
    assert get_product_cupo_by_stock_field(_product(None)) == 0


def test_cupo_negative_stock():
    assert get_product_cupo_by_stock_field(_product(-5)) == 0


def test_cupo_large_stock():
    assert get_product_cupo_by_stock_field(_product(9999)) == 9999
