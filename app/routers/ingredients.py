from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select, case

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption
from app.schemas.auth import UserResponse
from app.schemas.inventory import (
    IngredientAdjustmentRequest,
    IngredientCreate,
    IngredientResponse,
    IngredientUpdate,
    ConsumptionItemResponse,
    ConsumptionUpsertRequest,
)

router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc_stock(session: Session, ingredient_id: int) -> float:
    """Compute current stock for one ingredient from its movement history."""
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


def _bulk_stock_map(session: Session) -> dict[int, float]:
    """Return {ingredient_id: current_stock} for all ingredients in one query."""
    rows = session.exec(
        select(
            IngredientStockMovement.ingredient_id,
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
            ).label("stock"),
        ).group_by(IngredientStockMovement.ingredient_id)
    ).all()
    return {r.ingredient_id: float(r.stock) for r in rows}


def _to_response(ingredient: Ingredient, stock: float) -> IngredientResponse:
    return IngredientResponse(
        ingredient_id=ingredient.ingredient_id,
        name=ingredient.name,
        unit=ingredient.unit,
        description=ingredient.description,
        min_stock=ingredient.min_stock,
        is_active=ingredient.is_active,
        current_stock=stock,
        is_low_stock=stock < ingredient.min_stock,
    )


# ── Ingredient CRUD ───────────────────────────────────────────────────────────

@router.get("", response_model=list[IngredientResponse])
def list_ingredients(
    active_only: bool = Query(True),
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("ingredients:view")),
):
    stmt = select(Ingredient)
    if active_only:
        stmt = stmt.where(Ingredient.is_active == True)  # noqa: E712
    ingredients = session.exec(stmt).all()
    stock_map = _bulk_stock_map(session)
    return [_to_response(i, stock_map.get(i.ingredient_id, 0.0)) for i in ingredients]


@router.post("", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    data: IngredientCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("ingredients:manage")),
):
    ingredient = Ingredient(
        name=data.name,
        unit=data.unit,
        description=data.description,
        min_stock=data.min_stock,
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return _to_response(ingredient, 0.0)


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(
    ingredient_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("ingredients:view")),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    stock = _calc_stock(session, ingredient_id)
    return _to_response(ingredient, stock)


@router.patch("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("ingredients:manage")),
):
    ingredient = session.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(ingredient, field, value)
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    stock = _calc_stock(session, ingredient_id)
    return _to_response(ingredient, stock)


# ── Ingredient stock adjustments ──────────────────────────────────────────────

@router.post("/adjustments", response_model=dict)
def adjust_ingredient_stock(
    adjustment: IngredientAdjustmentRequest,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("ingredients:adjust")),
):
    ingredient = session.get(Ingredient, adjustment.ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")

    current_stock = _calc_stock(session, adjustment.ingredient_id)
    new_stock = current_stock + adjustment.quantity
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente. Actual: {current_stock} {ingredient.unit}",
        )

    movement = IngredientStockMovement(
        ingredient_id=adjustment.ingredient_id,
        system_user_id=user.id,
        movement_type="IN" if adjustment.quantity > 0 else "OUT",
        quantity=abs(adjustment.quantity),
        notes=f"{adjustment.reason.value}: {adjustment.notes or ''}".strip(": "),
    )
    session.add(movement)
    session.commit()
    session.refresh(movement)

    return {
        "message": "Ajuste de insumo registrado",
        "movement_id": movement.movement_id,
        "new_stock": new_stock,
        "unit": ingredient.unit,
    }


# ── Product consumption (recipe) ──────────────────────────────────────────────

@router.get("/products/{product_id}/consumption", response_model=list[ConsumptionItemResponse])
def get_product_consumption(
    product_id: int,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("consumption:manage")),
):
    rows = session.exec(
        select(ProductConsumption).where(ProductConsumption.product_id == product_id)
    ).all()
    result = []
    for row in rows:
        ing = session.get(Ingredient, row.ingredient_id)
        result.append(
            ConsumptionItemResponse(
                id=row.id,
                ingredient_id=row.ingredient_id,
                ingredient_name=ing.name if ing else "N/A",
                unit=ing.unit if ing else "",
                quantity_used=row.quantity_used,
            )
        )
    return result


@router.post(
    "/products/{product_id}/consumption",
    response_model=list[ConsumptionItemResponse],
    status_code=status.HTTP_200_OK,
)
def upsert_product_consumption(
    product_id: int,
    data: ConsumptionUpsertRequest,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("consumption:manage")),
):
    """
    Replace all consumption entries for a product.
    Send an empty items list to clear consumption (product becomes stock-only).
    """
    # Validate all ingredients exist
    for item in data.items:
        if not session.get(Ingredient, item.ingredient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insumo id {item.ingredient_id} no encontrado",
            )

    # Delete existing entries for this product
    existing = session.exec(
        select(ProductConsumption).where(ProductConsumption.product_id == product_id)
    ).all()
    for row in existing:
        session.delete(row)
    session.flush()

    # Insert new entries
    result = []
    for item in data.items:
        row = ProductConsumption(
            product_id=product_id,
            ingredient_id=item.ingredient_id,
            quantity_used=item.quantity_used,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        ing = session.get(Ingredient, item.ingredient_id)
        result.append(
            ConsumptionItemResponse(
                id=row.id,
                ingredient_id=row.ingredient_id,
                ingredient_name=ing.name if ing else "N/A",
                unit=ing.unit if ing else "",
                quantity_used=row.quantity_used,
            )
        )

    session.commit()
    return result
