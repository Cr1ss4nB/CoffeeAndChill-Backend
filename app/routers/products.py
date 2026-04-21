from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.catalog import Category, Product
from app.schemas.catalog import (
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:create")),
):
    if product_data.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El precio debe ser mayor a 0",
        )
    if product_data.stock_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El stock no puede ser negativo",
        )

    category = session.get(Category, product_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )

    product = Product(
        name=product_data.name,
        category_id=product_data.category_id,
        price=product_data.price,
        stock_quantity=product_data.stock_quantity,
        description=product_data.description,
        status=product_data.status,
        image_url=product_data.image_url,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:edit")),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    if product_data.name is not None:
        product.name = product_data.name
    if product_data.category_id is not None:
        category = session.get(Category, product_data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada",
            )
        product.category_id = product_data.category_id
    if product_data.price is not None:
        if product_data.price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El precio debe ser mayor a 0",
            )
        product.price = product_data.price
    if product_data.stock_quantity is not None:
        if product_data.stock_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El stock no puede ser negativo",
            )
        product.stock_quantity = product_data.stock_quantity
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.status is not None:
        product.status = product_data.status
    if product_data.image_url is not None:
        product.image_url = product_data.image_url

    session.commit()
    session.refresh(product)

    return product


@router.patch("/{product_id}/status", response_model=ProductResponse)
def update_product_status(
    product_id: int,
    status_data: ProductStatusUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:edit")),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )

    if status_data.status not in ["ACTIVE", "INACTIVE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado inválido. Debe ser ACTIVE o INACTIVE",
        )

    product.status = status_data.status
    session.commit()
    session.refresh(product)

    return product
