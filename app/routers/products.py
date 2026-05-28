import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_permission, require_role
from app.core.fulfillment import FulfillmentType
from app.models.catalog import Category, Product
from app.routers.catalog_utils import product_to_catalog_response
from app.schemas.catalog import ProductCreate, ProductResponse, ProductStatusUpdate, ProductUpdate
from app.schemas.auth import UserResponse

IMAGES_DIR = os.path.join(settings.MEDIA_DIR, "images")
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

router = APIRouter(tags=["Products"])


@router.post("/upload-image")
async def upload_product_image(
    file: UploadFile = File(...),
    user: UserResponse = Depends(require_role(["admin", "employee"])),
):
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(400, detail="Solo se permiten imágenes JPEG, PNG, WebP o GIF")
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(400, detail="La imagen no debe superar 5 MB")
    raw_name = file.filename or "image"
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(IMAGES_DIR, exist_ok=True)
    with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
        f.write(content)
    return {"image_url": f"/media/images/{filename}"}


def _assert_fulfillment(s: str) -> str:
    try:
        FulfillmentType(s)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="fulfillment_type debe ser STOCK, INGREDIENTS o BOTH",
        ) from e
    return s


@router.post("", response_model=ProductResponse, status_code=http_status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:create")),
):
    if product_data.price <= 0:
        raise HTTPException(status_code=400, detail="El precio debe ser mayor a 0")
    if product_data.stock_quantity < 0:
        raise HTTPException(status_code=400, detail="El stock no puede ser negativo")

    category = session.get(Category, product_data.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    ft = _assert_fulfillment(product_data.fulfillment_type)

    product = Product(
        name=product_data.name,
        category_id=product_data.category_id,
        price=product_data.price,
        stock_quantity=product_data.stock_quantity,
        description=product_data.description,
        status=product_data.status,
        image_url=product_data.image_url,
        fulfillment_type=ft,
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    return product_to_catalog_response(session, product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:edit")),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if product_data.name is not None:
        product.name = product_data.name
    if product_data.category_id is not None:
        category = session.get(Category, product_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        product.category_id = product_data.category_id
    if product_data.price is not None:
        if product_data.price <= 0:
            raise HTTPException(status_code=400, detail="El precio debe ser mayor a 0")
        product.price = product_data.price
    if product_data.stock_quantity is not None:
        if product_data.stock_quantity < 0:
            raise HTTPException(status_code=400, detail="El stock no puede ser negativo")
        product.stock_quantity = product_data.stock_quantity
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.status is not None:
        product.status = product_data.status
    if product_data.image_url is not None:
        product.image_url = product_data.image_url
    if product_data.fulfillment_type is not None:
        product.fulfillment_type = _assert_fulfillment(product_data.fulfillment_type)

    session.commit()
    session.refresh(product)

    return product_to_catalog_response(session, product)


@router.patch("/{product_id}/status", response_model=ProductResponse)
def update_product_status(
    product_id: int,
    status_data: ProductStatusUpdate,
    session: Session = Depends(get_db),
    user: UserResponse = Depends(require_permission("products:edit")),
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if status_data.status not in ["ACTIVE", "INACTIVE"]:
        raise HTTPException(status_code=400, detail="Estado inválido. Debe ser ACTIVE o INACTIVE")

    product.status = status_data.status
    session.commit()
    session.refresh(product)

    return product_to_catalog_response(session, product)
