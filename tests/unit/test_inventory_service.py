"""
Unit tests for inventory_service.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.models.inventory import Ingredient, IngredientStockMovement
from app.services.inventory_service import (
    adjust_stock,
    consume_ingredients,
    get_current_stock,
    get_inventory_summary,
    get_low_stock_items,
    record_movement,
    validate_stock_sufficient,
)


@pytest.fixture
def setup_ingredients(session: Session):
    """Create test ingredients."""
    ing1 = Ingredient(
        name="Coffee Beans",
        unit="g",
        description="Premium arabica",
        min_stock=100.0,
        is_active=True
    )
    ing2 = Ingredient(
        name="Milk",
        unit="ml",
        description="Whole milk",
        min_stock=500.0,
        is_active=True
    )
    ing3 = Ingredient(
        name="Sugar",
        unit="g",
        description="White sugar",
        min_stock=50.0,
        is_active=False  # Inactive ingredient
    )

    session.add(ing1)
    session.add(ing2)
    session.add(ing3)
    session.commit()

    return {
        "coffee": ing1,
        "milk": ing2,
        "sugar": ing3,
    }


class TestGetCurrentStock:
    """Tests for get_current_stock function."""

    def test_get_current_stock_zero(self, session: Session, setup_ingredients):
        """Test getting stock of ingredient with no movements."""
        ing = setup_ingredients["coffee"]
        stock = get_current_stock(session, ing.ingredient_id)

        assert stock == 0.0

    def test_get_current_stock_with_movements(self, session: Session, setup_ingredients):
        """Test getting stock after IN and OUT movements."""
        ing = setup_ingredients["coffee"]

        # Add IN movements
        mov1 = IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=1,
            movement_type="IN",
            quantity=100.0
        )
        mov2 = IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=1,
            movement_type="IN",
            quantity=50.0
        )
        session.add(mov1)
        session.add(mov2)
        session.commit()

        stock = get_current_stock(session, ing.ingredient_id)
        assert stock == 150.0

    def test_get_current_stock_with_deductions(self, session: Session, setup_ingredients):
        """Test stock calculation with SALE and OUT movements."""
        ing = setup_ingredients["milk"]

        # Add movements
        mov1 = IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=1,
            movement_type="IN",
            quantity=1000.0
        )
        mov2 = IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=1,
            movement_type="SALE",
            quantity=200.0
        )
        mov3 = IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=1,
            movement_type="WASTE",
            quantity=50.0
        )
        session.add(mov1)
        session.add(mov2)
        session.add(mov3)
        session.commit()

        stock = get_current_stock(session, ing.ingredient_id)
        assert stock == 750.0


class TestRecordMovement:
    """Tests for record_movement function."""

    def test_record_movement_success(self, session: Session, setup_ingredients):
        """Test successful movement recording."""
        ing = setup_ingredients["coffee"]

        movement = record_movement(
            session,
            ing.ingredient_id,
            "IN",
            100.0,
            notes="Initial stock"
        )

        assert movement.ingredient_id == ing.ingredient_id
        assert movement.movement_type == "IN"
        assert movement.quantity == 100.0
        assert movement.notes == "Initial stock"

    def test_record_movement_invalid_type(self, session: Session, setup_ingredients):
        """Test that invalid movement type raises error."""
        ing = setup_ingredients["coffee"]

        with pytest.raises(HTTPException) as exc_info:
            record_movement(session, ing.ingredient_id, "INVALID", 100.0)

        assert exc_info.value.status_code == 400

    def test_record_movement_zero_quantity(self, session: Session, setup_ingredients):
        """Test that zero quantity raises error."""
        ing = setup_ingredients["coffee"]

        with pytest.raises(HTTPException) as exc_info:
            record_movement(session, ing.ingredient_id, "IN", 0.0)

        assert exc_info.value.status_code == 400

    def test_record_movement_ingredient_not_found(self, session: Session):
        """Test that non-existent ingredient raises error."""
        with pytest.raises(HTTPException) as exc_info:
            record_movement(session, 999, "IN", 100.0)

        assert exc_info.value.status_code == 404


class TestAdjustStock:
    """Tests for adjust_stock function."""

    def test_adjust_stock_increase(self, session: Session, setup_ingredients):
        """Test increasing stock."""
        ing = setup_ingredients["coffee"]

        new_stock = adjust_stock(session, ing.ingredient_id, 100.0)

        assert new_stock == 100.0

    def test_adjust_stock_decrease(self, session: Session, setup_ingredients):
        """Test decreasing stock."""
        ing = setup_ingredients["coffee"]

        # First add some stock
        adjust_stock(session, ing.ingredient_id, 200.0)

        # Then decrease
        new_stock = adjust_stock(session, ing.ingredient_id, -50.0)

        assert new_stock == 150.0

    def test_adjust_stock_zero(self, session: Session, setup_ingredients):
        """Test that zero adjustment raises error."""
        ing = setup_ingredients["coffee"]

        with pytest.raises(HTTPException) as exc_info:
            adjust_stock(session, ing.ingredient_id, 0.0)

        assert exc_info.value.status_code == 400


class TestGetInventorySummary:
    """Tests for get_inventory_summary function."""

    def test_get_inventory_summary_empty(self, session: Session, setup_ingredients):
        """Test summary with no movements."""
        summary = get_inventory_summary(session)

        # Should include 2 active ingredients (sugar is inactive)
        assert summary["total_items"] == 2
        assert summary["low_stock_count"] == 2  # Both below min_stock

    def test_get_inventory_summary_with_stock(self, session: Session, setup_ingredients):
        """Test summary with stock levels."""
        ing = setup_ingredients["coffee"]

        # Add enough stock to exceed min_stock
        record_movement(session, ing.ingredient_id, "IN", 200.0)

        summary = get_inventory_summary(session)

        assert summary["total_items"] == 2
        # Coffee should not be low stock now
        coffee_item = [i for i in summary["items"] if i["ingredient_id"] == ing.ingredient_id][0]
        assert coffee_item["is_low_stock"] is False


class TestGetLowStockItems:
    """Tests for get_low_stock_items function."""

    def test_get_low_stock_items_none(self, session: Session, setup_ingredients):
        """Test when all items have sufficient stock."""
        ing = setup_ingredients["coffee"]

        # Add enough stock
        record_movement(session, ing.ingredient_id, "IN", 200.0)

        low_stock = get_low_stock_items(session)

        # Only milk should be low stock
        assert len(low_stock) == 1
        assert low_stock[0]["name"] == "Milk"

    def test_get_low_stock_items_custom_threshold(self, session: Session, setup_ingredients):
        """Test with custom threshold."""
        ing = setup_ingredients["coffee"]

        # Add some stock
        record_movement(session, ing.ingredient_id, "IN", 75.0)

        # Use custom threshold
        low_stock = get_low_stock_items(session, threshold=80.0)

        # Coffee is below custom threshold
        coffee = [i for i in low_stock if i["ingredient_id"] == ing.ingredient_id]
        assert len(coffee) > 0


class TestValidateStockSufficient:
    """Tests for validate_stock_sufficient function."""

    def test_validate_stock_sufficient_true(self, session: Session, setup_ingredients):
        """Test validation when stock is sufficient."""
        ing = setup_ingredients["coffee"]

        # Add stock
        record_movement(session, ing.ingredient_id, "IN", 100.0)

        result = validate_stock_sufficient(session, ing.ingredient_id, 50.0)

        assert result is True

    def test_validate_stock_sufficient_false(self, session: Session, setup_ingredients):
        """Test validation when stock is insufficient."""
        ing = setup_ingredients["coffee"]

        # Add only 50
        record_movement(session, ing.ingredient_id, "IN", 50.0)

        result = validate_stock_sufficient(session, ing.ingredient_id, 100.0)

        assert result is False

    def test_validate_stock_insufficient_ingredient_not_found(self, session: Session):
        """Test validation with non-existent ingredient."""
        with pytest.raises(HTTPException) as exc_info:
            validate_stock_sufficient(session, 999, 50.0)

        assert exc_info.value.status_code == 404


class TestConsumeIngredients:
    """Tests for consume_ingredients function."""

    def test_consume_ingredients_success(self, session: Session, setup_ingredients):
        """Test successful consumption."""
        coffee = setup_ingredients["coffee"]
        milk = setup_ingredients["milk"]

        # Add initial stock
        record_movement(session, coffee.ingredient_id, "IN", 500.0)
        record_movement(session, milk.ingredient_id, "IN", 1000.0)

        consumptions = [
            {"ingredient_id": coffee.ingredient_id, "quantity": 50.0},
            {"ingredient_id": milk.ingredient_id, "quantity": 100.0}
        ]

        result = consume_ingredients(session, consumptions)

        assert result is True
        assert get_current_stock(session, coffee.ingredient_id) == 450.0
        assert get_current_stock(session, milk.ingredient_id) == 900.0

    def test_consume_ingredients_insufficient_stock(self, session: Session, setup_ingredients):
        """Test consumption with insufficient stock."""
        coffee = setup_ingredients["coffee"]

        # Add only 30 units
        record_movement(session, coffee.ingredient_id, "IN", 30.0)

        consumptions = [
            {"ingredient_id": coffee.ingredient_id, "quantity": 50.0}
        ]

        with pytest.raises(HTTPException) as exc_info:
            consume_ingredients(session, consumptions)

        assert exc_info.value.status_code == 400

    def test_consume_ingredients_invalid_data(self, session: Session):
        """Test consumption with invalid data."""
        consumptions = [
            {"ingredient_id": None, "quantity": 50.0}
        ]

        with pytest.raises(HTTPException) as exc_info:
            consume_ingredients(session, consumptions)

        assert exc_info.value.status_code == 400
