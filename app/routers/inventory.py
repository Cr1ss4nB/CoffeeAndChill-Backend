from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select, case

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.catalog import Product
from app.models.inventory import InventoryMovement
from app.models.security import SystemUser
from app.schemas.auth import UserResponse
from app.schemas.inventory import (
    AdjustmentRequest,
    InventoryListResponse,
    InventoryResponse,
    MovementListResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=InventoryListResponse)
def get_inventory(
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("inventory:view")),
):
    offset = (page - 1) * limit

    product_query = select(Product).where(Product.status == "ACTIVE")

    if category_id:
        product_query = product_query.where(Product.category_id == category_id)

    total = session.exec(select(func.count()).select_from(product_query)).one()

    products = session.exec(product_query.offset(offset).limit(limit)).all()

    stock_query = select(
        InventoryMovement.product_id,
        func.coalesce(
            func.sum(
                case(
                    (
                        InventoryMovement.movement_type == "IN",
                        InventoryMovement.quantity,
                    ),
                    (
                        InventoryMovement.movement_type == "OUT",
                        -InventoryMovement.quantity,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("stock"),
    ).group_by(InventoryMovement.product_id)
    stock_results = session.exec(stock_query).all()
    stock_map = {r.product_id: r.stock for r in stock_results}

    items = []
    low_stock_count = 0
    for product in products:
        calculated_stock = stock_map.get(product.product_id, product.stock_quantity)
        is_low = calculated_stock < settings.LOW_STOCK_THRESHOLD
        if is_low:
            low_stock_count += 1

        items.append(
            InventoryResponse(
                product_id=product.product_id,
                name=product.name,
                category=product.category.category_name if product.category else "N/A",
                price=product.price,
                stock_quantity=calculated_stock,
                status=product.status,
                is_low_stock=is_low,
            )
        )

    return InventoryListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        low_stock_count=low_stock_count,
    )


@router.post("/adjustments", response_model=dict)
def create_adjustment(
    adjustment: AdjustmentRequest,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("inventory:adjust")),
):
    product = session.get(Product, adjustment.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    stock_query = select(
        func.coalesce(
            func.sum(
                case(
                    (
                        InventoryMovement.movement_type == "IN",
                        InventoryMovement.quantity,
                    ),
                    (
                        InventoryMovement.movement_type == "OUT",
                        -InventoryMovement.quantity,
                    ),
                    else_=0,
                )
            ),
            0,
        )
    ).where(InventoryMovement.product_id == adjustment.product_id)
    current_stock = session.exec(stock_query).one()

    new_stock = current_stock + adjustment.quantity
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No hay suficiente stock. Stock actual: {current_stock}",
        )

    movement = InventoryMovement(
        product_id=adjustment.product_id,
        system_user_id=user.id,
        movement_type="IN" if adjustment.quantity > 0 else "OUT",
        quantity=abs(adjustment.quantity),
        reason=adjustment.reason.value,
        notes=adjustment.notes,
    )
    session.add(movement)
    session.commit()
    session.refresh(movement)

    return {
        "message": "Ajuste de inventario creado exitosamente",
        "movement_id": movement.movement_id,
        "new_stock": new_stock,
    }


@router.get("/movements", response_model=MovementListResponse)
def get_movements(
    movement_type: Optional[str] = Query(None),
    product_id: Optional[int] = Query(None),
    system_user_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("movements:view")),
):
    offset = (page - 1) * limit

    query = select(InventoryMovement).order_by(InventoryMovement.movement_date.desc())

    if movement_type:
        query = query.where(InventoryMovement.movement_type == movement_type)
    if product_id:
        query = query.where(InventoryMovement.product_id == product_id)
    if system_user_id:
        query = query.where(InventoryMovement.system_user_id == system_user_id)
    if start_date:
        query = query.where(InventoryMovement.movement_date >= start_date)
    if end_date:
        query = query.where(InventoryMovement.movement_date <= end_date)

    total = session.exec(select(func.count()).select_from(query)).one()
    movements = session.exec(query.offset(offset).limit(limit)).all()

    results = []
    for m in movements:
        product = session.get(Product, m.product_id)
        system_user = session.get(SystemUser, m.system_user_id)
        results.append(
            {
                "movement_id": m.movement_id,
                "product_id": m.product_id,
                "product_name": product.name if product else "N/A",
                "system_user_id": m.system_user_id,
                "user_name": system_user.full_name if system_user else "N/A",
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "unit_cost": m.unit_cost,
                "reason": m.reason,
                "movement_date": m.movement_date.isoformat(),
            }
        )

    return MovementListResponse(
        items=results,
        total=total,
        page=page,
        limit=limit,
    )
