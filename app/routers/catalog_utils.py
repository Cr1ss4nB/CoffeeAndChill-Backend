from sqlmodel import Session

from app.models.catalog import Product
from app.schemas.catalog import ProductResponse
from app.services import availability as av


def product_to_catalog_response(session: Session, p: Product) -> ProductResponse:
    snap = av.compute_sellable_snapshot(session, p)
    return ProductResponse(
        product_id=p.product_id,
        name=p.name,
        category_id=p.category_id,
        price=p.price,
        stock_quantity=p.stock_quantity,
        status=p.status,
        description=p.description,
        image_url=p.image_url,
        fulfillment_type=snap["fulfillment_type"],
        available_to_sell=snap["available_to_sell"],
        max_units_by_ingredients=snap["max_units_by_ingredients"],
        max_units_by_product_stock=snap["max_units_by_product_stock"],
        ingredient_limited=snap["ingredient_limited"],
    )
