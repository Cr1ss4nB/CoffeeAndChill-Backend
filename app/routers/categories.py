from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlmodel import Session, select

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.catalog import Category
from app.schemas.auth import UserResponse
from app.schemas.catalog import (
    CategoryCreate,
    CategoryResponse,
    CategoryStatusUpdate,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=http_status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    if category_data.type not in ("PRODUCT", "WORKSHOP"):
        raise HTTPException(
            status_code=400,
            detail="type debe ser PRODUCT o WORKSHOP",
        )

    existing = session.exec(
        select(Category).where(Category.category_name == category_data.category_name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una categoría con ese nombre",
        )

    category = Category(
        category_name=category_data.category_name,
        type=category_data.type,
        description=category_data.description,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    if category_data.category_name is not None:
        existing = session.exec(
            select(Category).where(
                Category.category_name == category_data.category_name,
                Category.category_id != category_id,
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Ya existe una categoría con ese nombre",
            )
        category.category_name = category_data.category_name

    if category_data.description is not None:
        category.description = category_data.description

    if category_data.is_active is not None:
        category.is_active = category_data.is_active

    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch("/{category_id}/status", response_model=CategoryResponse)
def toggle_category_status(
    category_id: int,
    status_data: CategoryStatusUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("catalog:manage")),
):
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    category.is_active = status_data.is_active
    session.add(category)
    session.commit()
    session.refresh(category)
    return category