"""
Inventory service layer for managing ingredient stock and movements.

                            IngredientStockMovement.movement_type.in_(['OUT', 'SALE', 'WASTE', 'ADJUSTMENT']),
and low stock notifications.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlmodel import Session, case, func, select

from app.core.time import utc_now
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption


def get_current_stock(
    session: Session,
    ingredient_id: int
) -> float:
    """
    Get the current stock level for an ingredient.

    Args:
        session: Database session
        ingredient_id: ID of ingredient

    Returns:
        Current stock quantity as float
    """
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (IngredientStockMovement.movement_type == "IN", IngredientStockMovement.quantity),
                    (
                        IngredientStockMovement.movement_type.in_(["OUT", "SALE", "WASTE", "ADJUSTMENT"]),
                        -IngredientStockMovement.quantity,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).where(IngredientStockMovement.ingredient_id == ingredient_id)

    result = session.exec(stmt).one()
    return float(result)


def record_movement(
    session: Session,
    ingredient_id: int,
    movement_type: str,
    quantity: float,
    notes: Optional[str] = None,
    system_user_id: Optional[int] = None,
    related_order_id: Optional[int] = None
) -> IngredientStockMovement:
    """
                    return float(result)

                    result = session.exec(
                        select(
                            func.coalesce(
                                func.sum(
                                    case(
                                        (IngredientStockMovement.movement_type == "IN", IngredientStockMovement.quantity),
                                        (
                                            IngredientStockMovement.movement_type.in_(["OUT", "SALE", "WASTE", "ADJUSTMENT"]),
                                            -IngredientStockMovement.quantity,
                                        ),
                                        else_=0,
                                    )
                                ),
                                0,
                            )
                        ).where(IngredientStockMovement.ingredient_id == ingredient_id)
                    ).scalar_one()

                    return float(result)

    Args:
        session: Database session
        ingredient_id: ID of ingredient
        movement_type: Type of movement (IN, OUT, SALE, WASTE, ADJUSTMENT)
        quantity: Quantity moved
        notes: Optional notes about the movement
        system_user_id: ID of user recording the movement
        related_order_id: Optional related order ID

    Returns:
        Created IngredientStockMovement instance

    Raises:
        HTTPException: If ingredient not found or invalid data
    """
    # Validate ingredient exists
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )

    # Validate movement type
    valid_types = ["IN", "OUT", "SALE", "WASTE", "ADJUSTMENT"]
    if movement_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid movement type. Must be one of: {', '.join(valid_types)}"
        )

    # Validate quantity
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero"
        )

    # Create movement record
    movement = IngredientStockMovement(
        ingredient_id=ingredient_id,
        system_user_id=system_user_id or 1,  # Default to admin user
        movement_type=movement_type,
        quantity=quantity,
        notes=notes,
        related_order_id=related_order_id,
        movement_date=utc_now()
    )

    session.add(movement)
    session.commit()
    session.refresh(movement)

    return movement


def adjust_stock(
    session: Session,
    ingredient_id: int,
    quantity: float
) -> float:
    """
    Adjust ingredient stock by a delta amount (positive or negative).

    Args:
        session: Database session
        ingredient_id: ID of ingredient
        quantity: Quantity to adjust (positive to add, negative to remove)

    Returns:
        New stock level after adjustment

    Raises:
        HTTPException: If ingredient not found or adjustment invalid
    """
    # Validate ingredient exists
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )

    # Validate adjustment
    if quantity == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment quantity cannot be zero"
        )

    # Determine movement type and absolute quantity
    if quantity > 0:
        movement_type = "IN"
        abs_quantity = quantity
    else:
        movement_type = "ADJUSTMENT"
        abs_quantity = abs(quantity)

    # Record the movement
    movement = IngredientStockMovement(
        ingredient_id=ingredient_id,
        system_user_id=1,  # Default to admin
        movement_type=movement_type,
        quantity=abs_quantity,
        notes=f"Stock adjustment: {quantity}",
        movement_date=utc_now()
    )

    session.add(movement)
    session.commit()

    # Return new stock level
    return get_current_stock(session, ingredient_id)


def get_inventory_summary(session: Session) -> Dict[str, Any]:
    """
    Get a comprehensive summary of current inventory status.

    Args:
        session: Database session

    Returns:
        Dictionary containing inventory summary statistics
    """
    # Get all active ingredients
    ingredients = session.exec(
        select(Ingredient).where(Ingredient.is_active == True)  # noqa: E712
    ).all()

    total_value = 0.0
    low_stock_count = 0
    total_items = len(ingredients)
    items = []

    for ing in ingredients:
        stock = get_current_stock(session, ing.ingredient_id)
        is_low = stock < ing.min_stock

        if is_low:
            low_stock_count += 1

        items.append({
            "ingredient_id": ing.ingredient_id,
            "name": ing.name,
            "current_stock": stock,
            "unit": ing.unit,
            "min_stock": ing.min_stock,
            "is_low_stock": is_low
        })

    return {
        "total_items": total_items,
        "low_stock_count": low_stock_count,
        "items": items,
        "last_updated": utc_now().isoformat()
    }


def get_low_stock_items(
    session: Session,
    threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Get all ingredients with stock below their minimum or custom threshold.

    Args:
        session: Database session
        threshold: Optional custom threshold to use instead of ingredient min_stock

    Returns:
        List of low-stock ingredient dictionaries
    """
    ingredients = session.exec(
        select(Ingredient).where(Ingredient.is_active == True)  # noqa: E712
    ).all()

    low_stock_items = []

    for ing in ingredients:
        stock = get_current_stock(session, ing.ingredient_id)
        check_threshold = threshold if threshold is not None else ing.min_stock

        if stock < check_threshold:
            low_stock_items.append({
                "ingredient_id": ing.ingredient_id,
                "name": ing.name,
                "current_stock": stock,
                "unit": ing.unit,
                "min_stock": ing.min_stock,
                "threshold_used": check_threshold,
                "shortage": check_threshold - stock
            })

    # Sort by shortage (most critical first)
    low_stock_items.sort(key=lambda x: x["shortage"], reverse=True)

    return low_stock_items


def validate_stock_sufficient(
    session: Session,
    ingredient_id: int,
    required_quantity: float
) -> bool:
    """
    Check if there is sufficient stock of an ingredient.

    Args:
        session: Database session
        ingredient_id: ID of ingredient
        required_quantity: Quantity needed

    Returns:
        True if stock is sufficient, False otherwise

    Raises:
        HTTPException: If ingredient not found
    """
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )

    current_stock = get_current_stock(session, ingredient_id)
    return current_stock >= required_quantity


def consume_ingredients(
    session: Session,
    consumptions: List[Dict[str, Any]]
) -> bool:
    """
    Process consumption of multiple ingredients (for orders/recipes).

    Args:
        session: Database session
        consumptions: List of dicts with ingredient_id, quantity, related_order_id

    Returns:
        True if all consumptions processed successfully

    Raises:
        HTTPException: If any ingredient not found or stock insufficient
    """
    # First validate all consumptions
    for consumption in consumptions:
        ingredient_id = consumption.get("ingredient_id")
        quantity = consumption.get("quantity", 0)

        if not ingredient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ingredient_id required for each consumption"
            )

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Consumption quantity must be greater than zero"
            )

        ingredient = session.get(Ingredient, ingredient_id)
        if not ingredient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingredient {ingredient_id} not found"
            )

        # Validate sufficient stock
        if not validate_stock_sufficient(session, ingredient_id, quantity):
            ing_name = ingredient.name
            current = get_current_stock(session, ingredient_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock of {ing_name}. Have: {current}, Need: {quantity}"
            )

    # Record all consumption movements
    for consumption in consumptions:
        ingredient_id = consumption["ingredient_id"]
        quantity = consumption["quantity"]
        related_order_id = consumption.get("related_order_id")

        movement = IngredientStockMovement(
            ingredient_id=ingredient_id,
            system_user_id=consumption.get("system_user_id", 1),
            movement_type="SALE",
            quantity=quantity,
            related_order_id=related_order_id,
            movement_date=utc_now()
        )

        session.add(movement)

    session.commit()
    return True
