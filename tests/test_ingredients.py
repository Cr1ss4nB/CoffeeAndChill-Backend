"""
P0 — Tests para /ingredients (CRUD, ajustes de stock) y
/ingredients/products/{id}/consumption (recetas / upsert).
Cubre: listado con filtros, creación, actualización, desactivación,
ajuste de stock (positivo/negativo/overdraft), y toda la lógica
de recetas + auto-flip de fulfillment_type.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.catalog import Category, Product
from app.models.inventory import Ingredient

@pytest.fixture
def admin_token(client: TestClient, test_data) -> str:
    r = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def _make_ingredient(
    session: Session,
    name: str = "Café",
    unit: str = "g",
    min_stock: float = 50.0,
    is_active: bool = True,
) -> Ingredient:
    ing = Ingredient(name=name, unit=unit, min_stock=min_stock, is_active=is_active)
    session.add(ing)
    session.commit()
    session.refresh(ing)
    return ing

def _make_product(session: Session, fulfillment: str = "STOCK") -> Product:
    cat = Category(category_name="Cat", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    p = Product(
        name="Producto test",
        category_id=cat.category_id,
        price=3000.0,
        stock_quantity=0,
        fulfillment_type=fulfillment,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

def _add_stock(client: TestClient, token: str, ingredient_id: int, qty: float):
    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": ingredient_id, "quantity": qty, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

def test_list_ingredients_empty(client: TestClient, admin_token: str):
    r = client.get("/ingredients", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json() == []

def test_list_ingredients_active_only_default_excludes_inactive(
    client: TestClient, session: Session, admin_token: str
):
    _make_ingredient(session, name="Café activo")
    _make_ingredient(session, name="Azúcar inactivo", is_active=False)

    r = client.get("/ingredients", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    names = [i["name"] for i in r.json()]
    assert "Café activo" in names
    assert "Azúcar inactivo" not in names

def test_list_ingredients_active_only_false_includes_inactive(
    client: TestClient, session: Session, admin_token: str
):
    _make_ingredient(session, name="Café activo")
    _make_ingredient(session, name="Azúcar inactivo", is_active=False)

    r = client.get(
        "/ingredients?active_only=false",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    names = [i["name"] for i in r.json()]
    assert "Café activo" in names
    assert "Azúcar inactivo" in names

def test_list_ingredients_requires_auth(client: TestClient):
    r = client.get("/ingredients")
    assert r.status_code in (401, 403)

def test_create_ingredient(client: TestClient, admin_token: str):
    r = client.post(
        "/ingredients",
        json={"name": "Leche", "unit": "ml", "min_stock": 500.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Leche"
    assert data["unit"] == "ml"
    assert data["current_stock"] == 0.0
    assert data["is_low_stock"] is True  # 0 < min_stock=500

def test_create_ingredient_zero_min_stock(client: TestClient, admin_token: str):
    r = client.post(
        "/ingredients",
        json={"name": "Sal", "unit": "g", "min_stock": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201
    assert r.json()["is_low_stock"] is False  # 0 == 0, no es bajo

def test_create_ingredient_requires_auth(client: TestClient):
    r = client.post("/ingredients", json={"name": "X", "unit": "g", "min_stock": 0})
    assert r.status_code in (401, 403)

def test_get_ingredient(client: TestClient, session: Session, admin_token: str):
    ing = _make_ingredient(session, name="Cacao")
    r = client.get(
        f"/ingredients/{ing.ingredient_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Cacao"
    assert r.json()["current_stock"] == 0.0

def test_get_ingredient_not_found(client: TestClient, admin_token: str):
    r = client.get(
        "/ingredients/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_update_ingredient_name(client: TestClient, session: Session, admin_token: str):
    ing = _make_ingredient(session)
    r = client.patch(
        f"/ingredients/{ing.ingredient_id}",
        json={"name": "Café Premium"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Café Premium"

def test_update_ingredient_min_stock(client: TestClient, session: Session, admin_token: str):
    ing = _make_ingredient(session, min_stock=50.0)
    r = client.patch(
        f"/ingredients/{ing.ingredient_id}",
        json={"min_stock": 200.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["min_stock"] == 200.0

def test_deactivate_ingredient_hides_from_default_list(
    client: TestClient, session: Session, admin_token: str
):
    ing = _make_ingredient(session)
    r = client.patch(
        f"/ingredients/{ing.ingredient_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    list_r = client.get("/ingredients", headers={"Authorization": f"Bearer {admin_token}"})
    ids = [i["ingredient_id"] for i in list_r.json()]
    assert ing.ingredient_id not in ids

def test_update_ingredient_not_found(client: TestClient, admin_token: str):
    r = client.patch(
        "/ingredients/99999",
        json={"name": "X"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_adjust_stock_positive_creates_in_movement(
    client: TestClient, session: Session, admin_token: str
):
    ing = _make_ingredient(session)
    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": ing.ingredient_id, "quantity": 200.0, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["new_stock"] == 200.0
    assert data["unit"] == ing.unit

def test_adjust_stock_negative_decreases_stock(
    client: TestClient, session: Session, admin_token: str
):
    ing = _make_ingredient(session)
    _add_stock(client, admin_token, ing.ingredient_id, 500.0)

    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": ing.ingredient_id, "quantity": -150.0, "reason": "WASTE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json()["new_stock"] == 350.0

def test_adjust_stock_cumulative(
    client: TestClient, session: Session, admin_token: str
):
    ing = _make_ingredient(session)
    _add_stock(client, admin_token, ing.ingredient_id, 300.0)
    _add_stock(client, admin_token, ing.ingredient_id, 200.0)

    r = client.get(
        f"/ingredients/{ing.ingredient_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.json()["current_stock"] == 500.0

def test_adjust_stock_overdraft_blocked(
    client: TestClient, session: Session, admin_token: str
):
    ing = _make_ingredient(session)  # stock = 0

    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": ing.ingredient_id, "quantity": -50.0, "reason": "WASTE"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "insuficiente" in r.json()["detail"].lower()

def test_adjust_stock_ingredient_not_found(client: TestClient, admin_token: str):
    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": 99999, "quantity": 10.0, "reason": "RECEIPT"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_adjust_stock_requires_auth(client: TestClient, session: Session):
    ing = _make_ingredient(session)
    r = client.post(
        "/ingredients/adjustments",
        json={"ingredient_id": ing.ingredient_id, "quantity": 10.0, "reason": "RECEIPT"},
    )
    assert r.status_code in (401, 403)

def test_get_consumption_empty(client: TestClient, session: Session, admin_token: str):
    p = _make_product(session)
    r = client.get(
        f"/ingredients/products/{p.product_id}/consumption",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []

def test_upsert_consumption_creates_recipe(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    ing = _make_ingredient(session)

    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing.ingredient_id, "quantity_used": 18.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) == 1
    assert data[0]["ingredient_id"] == ing.ingredient_id
    assert data[0]["quantity_used"] == 18.0
    assert data[0]["ingredient_name"] == ing.name
    assert data[0]["unit"] == ing.unit

def test_upsert_consumption_flips_fulfillment_to_ingredients(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session, fulfillment="STOCK")
    ing = _make_ingredient(session)

    client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing.ingredient_id, "quantity_used": 10.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    session.refresh(p)
    assert p.fulfillment_type == "INGREDIENTS"

def test_upsert_consumption_replaces_previous_recipe(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    ing1 = _make_ingredient(session, name="Café")
    ing2 = _make_ingredient(session, name="Leche", unit="ml")

    client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing1.ingredient_id, "quantity_used": 18.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing2.ingredient_id, "quantity_used": 200.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["ingredient_id"] == ing2.ingredient_id

def test_upsert_empty_recipe_resets_fulfillment_to_stock(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    ing = _make_ingredient(session)

    client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing.ingredient_id, "quantity_used": 10.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    session.refresh(p)
    assert p.fulfillment_type == "INGREDIENTS"

    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []
    session.refresh(p)
    assert p.fulfillment_type == "STOCK"

def test_upsert_consumption_rejects_inactive_ingredient(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    inactive = _make_ingredient(session, name="Inactivo", is_active=False)

    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": inactive.ingredient_id, "quantity_used": 5.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 400
    assert "inactivo" in r.json()["detail"].lower()

def test_upsert_consumption_product_not_found(client: TestClient, admin_token: str):
    r = client.post(
        "/ingredients/products/99999/consumption",
        json={"items": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_upsert_consumption_ingredient_not_found(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": 99999, "quantity_used": 5.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 404

def test_upsert_consumption_multi_ingredient_recipe(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    ing1 = _make_ingredient(session, name="Café", unit="g")
    ing2 = _make_ingredient(session, name="Leche", unit="ml")
    ing3 = _make_ingredient(session, name="Azúcar", unit="g")

    r = client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={
            "items": [
                {"ingredient_id": ing1.ingredient_id, "quantity_used": 18.0},
                {"ingredient_id": ing2.ingredient_id, "quantity_used": 120.0},
                {"ingredient_id": ing3.ingredient_id, "quantity_used": 5.0},
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 3

def test_get_consumption_after_upsert(
    client: TestClient, session: Session, admin_token: str
):
    p = _make_product(session)
    ing = _make_ingredient(session)

    client.post(
        f"/ingredients/products/{p.product_id}/consumption",
        json={"items": [{"ingredient_id": ing.ingredient_id, "quantity_used": 25.0}]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    r = client.get(
        f"/ingredients/products/{p.product_id}/consumption",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["quantity_used"] == 25.0