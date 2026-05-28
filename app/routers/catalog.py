from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import true
from sqlmodel import Session, select

from app.core.database import get_db
from app.models.catalog import Category, Product
from app.routers.catalog_utils import product_to_catalog_response
from app.schemas.catalog import (
    CategoryResponse,
    ProductDetailResponse,
    ProductResponse,
)

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    session: Session = Depends(get_db),
    active_only: bool = Query(True, description="Filtrar solo categorías activas"),
):
    # Obtiene el listado de categorías del menú y talleres.
    stmt = select(Category)
    if active_only:
        stmt = stmt.where(Category.is_active == true()) 

    categories = session.exec(stmt).all()
    return categories


@router.get("/products", response_model=List[ProductResponse])
def get_products(
    session: Session = Depends(get_db),
    category_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    active_only: bool = Query(True, description="Mostrar solo productos con status ACTIVE"),
):
    stmt = select(Product)

    if active_only:
        stmt = stmt.where(Product.status == "ACTIVE")
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    products = session.exec(stmt).all()
    return [product_to_catalog_response(session, p) for p in products]


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: int,
    session: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .where(Product.product_id == product_id)
    )

    product = session.exec(stmt).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    category = session.get(Category, product.category_id)
    if not category:
        raise HTTPException(
            status_code=500,
            detail="Producto sin categoría cargada",
        )
    pr = product_to_catalog_response(session, product)
    return ProductDetailResponse(
        **pr.model_dump(),
        category=CategoryResponse.model_validate(category),
    )
