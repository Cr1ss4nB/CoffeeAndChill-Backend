"""
Disponibilidad (receta vs stock) y checkout.
"""
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption
from app.models.security import SystemUser
from app.services import availability as av


def _ingredient_stock(session: Session, amount: float) -> tuple[Category, Ingredient, SystemUser]:
    admin = session.exec(
        select(SystemUser).where(SystemUser.email == "admin@example.com")
    ).first()
    assert admin is not None
    cat = Category(category_name="CatF", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    ing = Ingredient(name="Café test", unit="g", min_stock=0, is_active=True)
    session.add(ing)
    session.commit()
    session.refresh(ing)
    session.add(
        IngredientStockMovement(
            ingredient_id=ing.ingredient_id,
            system_user_id=admin.system_user_id,
            movement_type="IN",
            quantity=amount,
            notes="test",
        )
    )
    session.commit()
    return cat, ing, admin


def test_ingredients_policy_available_ignores_zero_product_stock(
    client: TestClient, session: Session, test_data
):
    cat, ing, _ = _ingredient_stock(session, 1000.0)
    p = Product(
        name="Américano test",
        category_id=cat.category_id,
        price=1.0,
        stock_quantity=0,
        fulfillment_type="INGREDIENTS",
        status="ACTIVE",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    session.add(
        ProductConsumption(
            product_id=p.product_id,
            ingredient_id=ing.ingredient_id,
            quantity_used=18.0,
        )
    )
    session.commit()

    p = session.get(Product, p.product_id)  # refresh
    snap = av.compute_sellable_snapshot(session, p)
    assert snap["available_to_sell"] == 55  # 1000 // 18
    assert snap["max_units_by_product_stock"] == 0

    r = client.get(f"/catalog/products/{p.product_id}")
    assert r.status_code == 200
    assert r.json()["available_to_sell"] == 55


def test_checkout_ingredients_policy_does_not_decrement_product_row(
    client: TestClient, session: Session, test_data
):
    cat, ing, _ = _ingredient_stock(session, 1000.0)
    p = Product(
        name="Latte f",
        category_id=cat.category_id,
        price=10.0,
        stock_quantity=0,
        fulfillment_type="INGREDIENTS",
        status="ACTIVE",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    session.add(
        ProductConsumption(
            product_id=p.product_id, ingredient_id=ing.ingredient_id, quantity_used=20.0
        )
    )
    session.commit()

    login = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "customerpass"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    r = client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"order_type": "TAKEAWAY", "items": [{"product_id": p.product_id, "quantity": 1}]},
    )
    assert r.status_code == 201, r.text
    session.refresh(p)
    assert p.stock_quantity == 0


def test_stock_only_blocks_on_row_quantity(
    client: TestClient, session: Session, test_data
):
    cat = Category(category_name="Solo s", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    p = Product(
        name="Galleta",
        category_id=cat.category_id,
        price=1.0,
        stock_quantity=1,
        fulfillment_type="STOCK",
        status="ACTIVE",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    login = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "customerpass"},
    )
    token = login.json()["access_token"]
    r = client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"order_type": "TAKEAWAY", "items": [{"product_id": p.product_id, "quantity": 5}]},
    )
    assert r.status_code == 400
    assert "Stock insuficiente" in r.json()["detail"]


def test_recipe_insufficient_blocks(client: TestClient, session: Session, test_data):
    cat, ing, _ = _ingredient_stock(session, 1000.0)
    p = Product(
        name="Caf f",
        category_id=cat.category_id,
        price=1.0,
        stock_quantity=0,
        fulfillment_type="INGREDIENTS",
        status="ACTIVE",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    session.add(
        ProductConsumption(
            product_id=p.product_id, ingredient_id=ing.ingredient_id, quantity_used=500.0
        )
    )
    session.commit()
    p = session.get(Product, p.product_id)
    assert av.compute_sellable_snapshot(session, p)["available_to_sell"] == 2

    login = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "customerpass"},
    )
    token = login.json()["access_token"]
    r = client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"order_type": "TAKEAWAY", "items": [{"product_id": p.product_id, "quantity": 3}]},
    )
    assert r.status_code == 400
