from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.catalog import Category, Product
from app.schemas.catalog import CategoryResponse, ProductResponse, ProductDetailResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    session: Session = Depends(get_session),
    active_only: bool = Query(True, description="Filtrar solo categorías activas")
):
    """Obtiene el listado de categorías del menú y talleres."""
    stmt = select(Category)
    if active_only:
        stmt = stmt.where(Category.is_active == True)
    
    categories = session.exec(stmt).all()
    return categories


@router.get("/products", response_model=List[ProductResponse])
def get_products(
    session: Session = Depends(get_session),
    category_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    active_only: bool = Query(True, description="Mostrar solo productos con status ACTIVE")
):
    """Obtiene el catálogo de productos disponibles."""
    stmt = select(Product)
    
    if active_only:
        stmt = stmt.where(Product.status == "ACTIVE")
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
        
    products = session.exec(stmt).all()
    return products


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: int,
    session: Session = Depends(get_session)
):
    """Obtiene el detalle completo de un producto específico, incluyendo su categoría."""
    stmt = select(Product).where(Product.product_id == product_id).options(selectinload(Product.category))
    product = session.exec(stmt).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
        
    return product
