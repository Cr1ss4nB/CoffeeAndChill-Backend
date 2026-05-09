from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.catalog import Product, RecipeItem
from app.models.inventory import Ingredient, IngredientStockMovement, InventoryMovement, ProductConsumption
from app.models.operations import Order, OrderItem
from app.models.security import SystemUser
from app.schemas.auth import UserResponse
from app.schemas.order import CheckoutRequest
from app.services import availability as av


def _resolve_system_user_id(session: Session, current_user: UserResponse) -> int:
    if current_user.role != "client":
        return current_user.id
    admin = session.exec(select(SystemUser).where(SystemUser.is_active)).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No hay usuario de sistema activo para registrar la venta",
        )
    return int(admin.system_user_id)


def process_checkout(
    session: Session, checkout_data: CheckoutRequest, current_user: UserResponse
) -> Order:
    """
    Una sola transacción: valida cupo (producto + receta) y aplica movimientos.
    """
    if not checkout_data.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    total_amount = 0.0
    order_items_data: list[dict] = []
    system_user_id = _resolve_system_user_id(session, current_user)
    customer_id = current_user.id if current_user.role == "client" else None

    # Cantidad total por producto (líneas duplicadas)
    qty_by_product: dict[int, int] = defaultdict(int)
    for item_data in checkout_data.items:
        qty_by_product[item_data.product_id] += item_data.quantity

    # Fase 1: validar todo antes de tocar el estado
    for product_id, total_q in qty_by_product.items():
        product = session.get(Product, product_id)
        if not product or product.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto id {product_id} no existe o no está activo",
            )
        if total_q < 1:
            raise HTTPException(status_code=400, detail="La cantidad debe ser >= 1")

        snap = av.compute_sellable_snapshot(session, product)
        if total_q > snap["available_to_sell"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stock insuficiente para {product.name}. "
                    f"Disponible: {snap['available_to_sell']}. "
                    f"(producto: {snap['max_units_by_product_stock']}, "
                    f"receta: {snap['max_units_by_ingredients']!s})"
                ),
            )
        ok, err = av.validate_recipe_allows_ingredient_deduction(session, product, total_q)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err or "Insumos insuficientes")

    # Preparar ítems y subtotales
    for item_data in checkout_data.items:
        product = session.get(Product, item_data.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        subtotal = float(product.price) * item_data.quantity
        total_amount += subtotal
        order_items_data.append(
            {
                "product": product,
                "quantity": item_data.quantity,
                "subtotal": subtotal,
                "special": item_data.special_instructions,
            }
        )

    order = Order(
        customer_id=customer_id,
        system_user_id=system_user_id,
        table_id=checkout_data.table_id,
        order_type=checkout_data.order_type,
        status="PENDING",
        subtotal=total_amount,
        tax_amount=0.0,
        discount_amount=0.0,
        total_amount=total_amount,
        order_date=datetime.now(timezone.utc),
        notes=checkout_data.notes,
    )
    session.add(order)
    session.flush()

    for entry in order_items_data:
        product = entry["product"]
        qty = entry["quantity"]
        recipe = session.exec(
            select(ProductConsumption).where(ProductConsumption.product_id == product.product_id)
        ).all()
        has_recipe = len(recipe) > 0
        dec_stock = av.should_decrement_product_stock(product.fulfillment_type, has_recipe)
        rec_m = av.should_record_product_inventory_movement(product.fulfillment_type, has_recipe)

        if dec_stock and product.stock_quantity < qty:
            session.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Condición de carrera: stock bajo de {product.name} al confirmar. Reintente.",
            )
        if dec_stock:
            product.stock_quantity -= qty
            session.add(product)

        item = OrderItem(
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=qty,
            unit_price=product.price,
            subtotal=entry["subtotal"],
            item_type="PRODUCT",
            status="PENDING",
            special_instructions=entry["special"],
        )
        session.add(item)

        if rec_m:
            session.add(
                InventoryMovement(
                    product_id=product.product_id,
                    system_user_id=system_user_id,
                    movement_type="SALE",
                    quantity=qty,
                    related_order_id=order.order_id,
                    notes=f"Venta orden #{order.order_id}",
                )
            )

        if has_recipe:
            for consumption in recipe:
                total_consumed = consumption.quantity_used * qty
                ing = session.get(Ingredient, consumption.ingredient_id)
                if not ing or not ing.is_active:
                    continue
                session.add(
                    IngredientStockMovement(
                        ingredient_id=consumption.ingredient_id,
                        system_user_id=system_user_id,
                        movement_type="SALE",
                        quantity=total_consumed,
                        related_order_id=order.order_id,
                        notes=f"Venta orden #{order.order_id} · {ing.name}",
                    )
                )

    session.commit()
    session.refresh(order)
    return order
