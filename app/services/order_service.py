from fastapi import HTTPException, status
from sqlmodel import Session, func, select, case
from datetime import datetime, timezone

from app.models.catalog import Product
from app.models.inventory import Ingredient, IngredientStockMovement, InventoryMovement, ProductConsumption
from app.models.operations import Order, OrderItem
from app.schemas.order import CheckoutRequest
from app.schemas.auth import UserResponse


def _get_ingredient_stock(session: Session, ingredient_id: int) -> float:
    result = session.exec(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (IngredientStockMovement.movement_type == "IN", IngredientStockMovement.quantity),
                        (
                            IngredientStockMovement.movement_type.in_(["OUT", "SALE", "WASTE"]),
                            -IngredientStockMovement.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(IngredientStockMovement.ingredient_id == ingredient_id)
    ).one()
    return float(result)


def process_checkout(
    session: Session, checkout_data: CheckoutRequest, current_user: UserResponse
) -> Order:
    """
    Business logic for processing a shopping cart and creating an order.
    Validates products, computes safe subtotals, reduces stock and saves securely.
    """
    total_amount = 0.0
    order_items_to_save = []
    sale_movements_to_save: list[dict] = []

    for item_data in checkout_data.items:
        # Get product via DB to ensure source of truth for price and stock
        product = session.get(Product, item_data.product_id)
        if not product or product.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto id {item_data.product_id} no existe o no está activo",
            )

        if product.stock_quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para {product.name}. Disponible: {product.stock_quantity}",
            )

        # Deduct stock
        product.stock_quantity -= item_data.quantity
        session.add(product)

        # Calculate secure subtotal
        item_subtotal = float(product.price) * item_data.quantity
        total_amount += item_subtotal

        # Build Order Item (without parent Order ID yet)
        order_item = OrderItem(
            product_id=product.product_id,
            quantity=item_data.quantity,
            unit_price=product.price,
            subtotal=item_subtotal,
            item_type="PRODUCT",
            status="PENDING",
            special_instructions=item_data.special_instructions,
        )
        order_items_to_save.append(order_item)

        # Collect data for SALE movement (order_id not available yet)
        sale_movements_to_save.append(
            {"product_id": product.product_id, "quantity": item_data.quantity}
        )

    system_user_id = 1
    if current_user.role != "client":
        system_user_id = current_user.id
        customer_id = None
    else:
        customer_id = current_user.id
        from app.models.security import SystemUser

        sys_admin = session.exec(
            select(SystemUser).where(SystemUser.is_active)
        ).first()
        if sys_admin:
            system_user_id = sys_admin.system_user_id

    order = Order(
        customer_id=customer_id,
        system_user_id=system_user_id,
        table_id=checkout_data.table_id,
        order_type=checkout_data.order_type,
        status="PENDING",
        subtotal=total_amount,
        tax_amount=0,  # Simplification
        discount_amount=0,
        total_amount=total_amount,
        order_date=datetime.now(timezone.utc),
        notes=checkout_data.notes,
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    # Attach order ID to items and write SALE movements for audit trail
    for item in order_items_to_save:
        item.order_id = order.order_id
        session.add(item)

    for mv in sale_movements_to_save:
        session.add(
            InventoryMovement(
                product_id=mv["product_id"],
                system_user_id=system_user_id,
                movement_type="SALE",
                quantity=mv["quantity"],
                related_order_id=order.order_id,
                notes=f"Venta orden #{order.order_id}",
            )
        )

        # Optional ingredient deduction: only runs if product has consumption configured.
        # Products without consumption entries are treated as stock-only (no ingredient tracking).
        consumptions = session.exec(
            select(ProductConsumption).where(
                ProductConsumption.product_id == mv["product_id"]
            )
        ).all()

        for consumption in consumptions:
            total_consumed = consumption.quantity_used * mv["quantity"]
            ingredient = session.get(Ingredient, consumption.ingredient_id)
            if ingredient and ingredient.is_active:
                current = _get_ingredient_stock(session, consumption.ingredient_id)
                if current < total_consumed:
                    # Soft warning via notes — does NOT block the sale.
                    # Ingredient stock can go negative to allow manual correction later.
                    notes = (
                        f"[STOCK BAJO] Venta orden #{order.order_id}. "
                        f"Disponible: {current} {ingredient.unit}"
                    )
                else:
                    notes = f"Venta orden #{order.order_id}"
                session.add(
                    IngredientStockMovement(
                        ingredient_id=consumption.ingredient_id,
                        system_user_id=system_user_id,
                        movement_type="SALE",
                        quantity=total_consumed,
                        related_order_id=order.order_id,
                        notes=notes,
                    )
                )

    session.commit()
    session.refresh(order)

    return order
