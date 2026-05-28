from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.fulfillment import FulfillmentType
from app.models.catalog import Product
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
from app.services.inventory_service import (
    get_current_stock,
    record_movement,
    get_low_stock_items,
)
from app.services.availability import get_ingredient_current_stock

router = APIRouter(tags=["Ingredients"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bulk_stock_map(session: Session) -> dict[int, float]:
    """Return {ingredient_id: current_stock} for all ingredients in one query."""
    ingredients = session.exec(select(Ingredient)).all()
    return {i.ingredient_id: get_current_stock(session, i.ingredient_id) for i in ingredients}


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
    stock = get_ingredient_current_stock(session, ingredient_id)
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
    stock = get_ingredient_current_stock(session, ingredient_id)
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

    current_stock = get_ingredient_current_stock(session, adjustment.ingredient_id)
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
    Reemplaza la receta (fuente de verdad). Lista vacía = sin receta, el producto pasa
    a política `STOCK` salvo que se ajuste en /products.

    Tras añadir líneas, si el producto estaba en `STOCK` se ajusta a `INGREDIENTS`
    (cupo llevado por insumos; cambiar a `BOTH` en /products si hace falta mín. con
    unidades de producto en almacén).
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    for item in data.items:
        ing = session.get(Ingredient, item.ingredient_id)
        if not ing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insumo id {item.ingredient_id} no encontrado",
            )
        if not ing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insumo inactivo: {ing.name} (ingredient_id {ing.ingredient_id})",
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

    if data.items:
        if product.fulfillment_type == FulfillmentType.STOCK.value:
            product.fulfillment_type = FulfillmentType.INGREDIENTS.value
    else:
        product.fulfillment_type = FulfillmentType.STOCK.value
    session.add(product)
    session.commit()
    return result
