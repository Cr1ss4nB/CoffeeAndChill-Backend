"""
P1 — Tests para GET /inventory, POST /inventory/adjustments, GET /inventory/movements.
Cubre: listado paginado con available_to_sell, low_stock_count, filtros,
ajustes de stock (IN/OUT/overdraft), y consulta de movimientos.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product
from app.models.inventory import Ingredient, IngredientStockMovement, InventoryMovement, ProductConsumption

@pytest.fixture
def admin_token(client: TestClient, test_data) -> str:
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def _make_category(session: Session, name: str = "Bebidas") -> Category:
    cat = Category(category_name=name, type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat

def _make_product(
    session: Session,
    category_id: int,
    name: str = "Espresso",
    price: float = 3500.0,
    stock: int = 10,
    status: str = "ACTIVE",
    fulfillment: str = "STOCK",
) -> Product:
    p = Product(
        name=name,
        category_id=category_id,
        price=price,
        stock_quantity=stock,
        status=status,
        fulfillment_type=fulfillment,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

def _make_ingredient(session: Session, name: str = "Café", stock: float = 0.0) -> Ingredient:
    ing = Ingredient(name=name, unit="g", min_stock=0, is_active=True)
    session.add(ing)
    session.commit()
    session.refresh(ing)
    return ing

def _add_inventory_movement(
    session: Session,
    product_id: int,
    system_user_id: int,
    quantity: int,
    movement_type: str = "IN",
) -> InventoryMovement:
    m = InventoryMovement(
        product_id=product_id,
        system_user_id=system_user_id,
        movement_type=movement_type,
        quantity=quantity,
        notes="test",
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m

def test_get_inventory_empty(client: TestClient, admin_token: str):
    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["low_stock_count"] == 0

def test_get_inventory_returns_active_products(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    _make_product(session, cat.category_id, name="Americano", stock=20)
    _make_product(session, cat.category_id, name="Inactivo", status="INACTIVE")

    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    names = [i["name"] for i in data["items"]]
    assert "Americano" in names
    assert "Inactivo" not in names

def test_get_inventory_item_fields(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    _make_product(session, cat.category_id, name="Latte", price=4500.0, stock=15)

    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["name"] == "Latte"
    assert item["price"] == 4500.0
    assert item["available_to_sell"] == 15
    assert item["fulfillment_type"] == "STOCK"
    assert "is_low_stock" in item
    assert "category" in item

def test_get_inventory_low_stock_count(
    client: TestClient, session: Session, admin_token: str
):
    """Productos con available_to_sell < LOW_STOCK_THRESHOLD (10) incrementan low_stock_count."""
    cat = _make_category(session)
    _make_product(session, cat.category_id, name="Bajo", stock=3)     # < 10 → low
    _make_product(session, cat.category_id, name="Normal", stock=50)  # >= 10 → ok

    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["low_stock_count"] == 1

def test_get_inventory_is_low_stock_flag(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    _make_product(session, cat.category_id, name="Bajo", stock=2)

    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    item = r.json()["items"][0]
    assert item["is_low_stock"] is True

def test_get_inventory_ingredients_product_available_to_sell(
    client: TestClient, session: Session, admin_token: str, test_data
):
    """Producto INGREDIENTS: available_to_sell calculado por receta, no por stock_quantity."""
    from app.models.security import SystemUser
    from sqlmodel import select

    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()

    cat = _make_category(session)
    p = _make_product(session, cat.category_id, name="Cappuccino", stock=0, fulfillment="INGREDIENTS")
    ing = _make_ingredient(session, name="Leche")

    # Agregar stock al ingrediente via movimiento directo
    session.add(IngredientStockMovement(
        ingredient_id=ing.ingredient_id,
        system_user_id=admin.system_user_id,
        movement_type="IN",
        quantity=500.0,
        notes="test",
    ))
    session.add(ProductConsumption(
        product_id=p.product_id,
        ingredient_id=ing.ingredient_id,
        quantity_used=100.0,  # 500 / 100 = 5 unidades
    ))
    session.commit()

    r = client.get("/inventory", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["name"] == "Cappuccino")
    assert item["available_to_sell"] == 5
    assert item["ingredient_limited"] is True

def test_get_inventory_filter_by_category(
    client: TestClient, session: Session, admin_token: str
):
    cat_a = _make_category(session, "Bebidas")
    cat_b = _make_category(session, "Comida")
    _make_product(session, cat_a.category_id, name="Café")
    _make_product(session, cat_b.category_id, name="Tostada")

    r = client.get(
        f"/inventory?category_id={cat_a.category_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert "Café" in names
    assert "Tostada" not in names

def test_get_inventory_pagination(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    for i in range(5):
        _make_product(session, cat.category_id, name=f"Prod {i}", stock=10)

    r = client.get("/inventory?page=1&limit=2", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["limit"] == 2

def test_get_inventory_requires_auth(client: TestClient):
    r = client.get("/inventory")
    assert r.status_code in (401, 403)

def test_adjustment_positive_creates_in_movement(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, stock=0)

    r = client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": 50, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["new_stock"] == 50
    assert "movement_id" in data

def test_adjustment_negative_decreases_stock(
    client: TestClient, session: Session, admin_token: str, test_data
):
    from app.models.security import SystemUser
    from sqlmodel import select

    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, stock=0)

    # Agregar stock previo via movimiento directo
    _add_inventory_movement(session, p.product_id, admin.system_user_id, 100, "IN")

    r = client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": -30, "reason": "WASTE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["new_stock"] == 70

def test_adjustment_cumulative(
    client: TestClient, session: Session, admin_token: str
):
    """El campo new_stock de cada ajuste acumula los movimientos correctamente."""
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, stock=0)

    client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": 40, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    r2 = client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": 60, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["new_stock"] == 100

def test_adjustment_overdraft_blocked(
    client: TestClient, session: Session, admin_token: str
):
    """Sacar más de lo disponible debe retornar 400."""
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, stock=0)  # sin movimientos previos

    r = client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": -10, "reason": "WASTE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "stock" in r.json()["detail"].lower()

def test_adjustment_product_not_found(client: TestClient, admin_token: str):
    r = client.post(
        "/inventory/adjustments",
        json={"product_id": 99999, "quantity": 10, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_adjustment_requires_auth(client: TestClient, session: Session):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id)

    r = client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": 10, "reason": "RECEIPT"},
    )
    assert r.status_code in (401, 403)

def test_get_movements_empty(client: TestClient, admin_token: str):
    r = client.get("/inventory/movements", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_get_movements_after_adjustment(
    client: TestClient, session: Session, admin_token: str
):
    cat = _make_category(session)
    p = _make_product(session, cat.category_id)

    client.post(
        "/inventory/adjustments",
        json={"product_id": p.product_id, "quantity": 25, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    r = client.get("/inventory/movements", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    mv = data["items"][0]
    assert mv["product_id"] == p.product_id
    assert mv["movement_type"] == "IN"
    assert mv["quantity"] == 25

def test_get_movements_filter_by_movement_type(
    client: TestClient, session: Session, admin_token: str, test_data
):
    from app.models.security import SystemUser
    from sqlmodel import select

    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    cat = _make_category(session)
    p = _make_product(session, cat.category_id)

    _add_inventory_movement(session, p.product_id, admin.system_user_id, 100, "IN")
    _add_inventory_movement(session, p.product_id, admin.system_user_id, 20, "OUT")

    r = client.get(
        "/inventory/movements?movement_type=IN",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    types = [m["movement_type"] for m in r.json()["items"]]
    assert all(t == "IN" for t in types)
    assert len(types) == 1

def test_get_movements_filter_by_product_id(
    client: TestClient, session: Session, admin_token: str, test_data
):
    from app.models.security import SystemUser
    from sqlmodel import select

    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    cat = _make_category(session)
    p1 = _make_product(session, cat.category_id, name="P1")
    p2 = _make_product(session, cat.category_id, name="P2")

    _add_inventory_movement(session, p1.product_id, admin.system_user_id, 10, "IN")
    _add_inventory_movement(session, p2.product_id, admin.system_user_id, 20, "IN")

    r = client.get(
        f"/inventory/movements?product_id={p1.product_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    ids = [m["product_id"] for m in r.json()["items"]]
    assert all(i == p1.product_id for i in ids)
    assert len(ids) == 1

def test_get_movements_after_checkout_records_sale(
    client: TestClient, session: Session, admin_token: str, test_data
):
    """Checkout de producto STOCK genera movimiento tipo SALE en inventory/movements."""
    cat = _make_category(session)
    p = _make_product(session, cat.category_id, name="Galleta", stock=10, fulfillment="STOCK")

    login = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "customerpass"}
    )
    token = login.json()["access_token"]

    client.post(
        "/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"order_type": "TAKEAWAY", "items": [{"product_id": p.product_id, "quantity": 2}]},
    )

    r = client.get(
        f"/inventory/movements?product_id={p.product_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    types = [m["movement_type"] for m in r.json()["items"]]
    assert "SALE" in types

def test_get_movements_requires_auth(client: TestClient):
    r = client.get("/inventory/movements")
    assert r.status_code in (401, 403)