from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.dependencies import get_current_user, require_permission
from app.core.security import hash_password
from app.models.catalog import Category, Product
from app.models.inventory import InventoryMovement
from app.models.security import SystemUser
from app.schemas.auth import UserResponse
from app.schemas.inventory import InventoryListResponse, InventoryResponse

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
                func.case(
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
