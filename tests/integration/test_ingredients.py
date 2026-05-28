"""Integration tests for app/routers/ingredients.py."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.inventory import Ingredient, IngredientStockMovement
from app.models.security import SystemUser
from tests.conftest import DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(client: TestClient, test_data) -> dict:
    token = _login(client, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def active_ingredient(session: Session, test_data) -> Ingredient:
    ing = Ingredient(name="Café molido", unit="g", min_stock=100, is_active=True)
    session.add(ing)
    session.commit()
    session.refresh(ing)
    return ing


@pytest.fixture
def inactive_ingredient(session: Session, test_data) -> Ingredient:
    ing = Ingredient(name="Azúcar vieja", unit="g", min_stock=0, is_active=False)
    session.add(ing)
    session.commit()
    session.refresh(ing)
    return ing


@pytest.fixture
def ingredient_with_stock(session: Session, test_data, active_ingredient: Ingredient) -> Ingredient:
    admin = session.exec(select(SystemUser).where(SystemUser.email == "admin@example.com")).first()
    session.add(
        IngredientStockMovement(
            ingredient_id=active_ingredient.ingredient_id,
            system_user_id=admin.system_user_id,
            movement_type="IN",
            quantity=500.0,
            notes="stock inicial test",
        )
    )
    session.commit()
    return active_ingredient


@pytest.fixture
def product_for_recipe(session: Session, test_data) -> Product:
    cat = Category(category_name="Bebidas", type="PRODUCT", description="")
    session.add(cat)
    session.commit()
    prod = Product(
        name="Espresso",
        category_id=cat.category_id,
        price=150.0,
        stock_quantity=10,
        status="ACTIVE",
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod


# ---------------------------------------------------------------------------
# GET /ingredients
# ---------------------------------------------------------------------------


def test_list_ingredients_active_only(
    client: TestClient,
    admin_headers: dict,
    active_ingredient,
    inactive_ingredient,
    test_data,
):
    r = client.get("/api/v1/admin/ingredients", headers=admin_headers)
    assert r.status_code == 200
    names = [i["name"] for i in r.json()]
    assert active_ingredient.name in names
    assert inactive_ingredient.name not in names


def test_list_ingredients_include_inactive(
    client: TestClient,
    admin_headers: dict,
    active_ingredient,
    inactive_ingredient,
    test_data,
):
    r = client.get("/api/v1/admin/ingredients?active_only=false", headers=admin_headers)
    assert r.status_code == 200
    names = [i["name"] for i in r.json()]
    assert active_ingredient.name in names
    assert inactive_ingredient.name in names


# ---------------------------------------------------------------------------
# POST /ingredients
# ---------------------------------------------------------------------------


def test_create_ingredient_success(client: TestClient, admin_headers: dict, test_data):
    r = client.post(
        "/api/v1/admin/ingredients",
        headers=admin_headers,
        json={
            "name": "Leche entera",
            "unit": "ml",
            "min_stock": 200,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Leche entera"
    assert data["current_stock"] == 0


# ---------------------------------------------------------------------------
# GET /ingredients/{id}
# ---------------------------------------------------------------------------


def test_get_ingredient_with_stock(
    client: TestClient, admin_headers: dict, ingredient_with_stock, test_data
):
    r = client.get(
        f"/api/v1/admin/ingredients/{ingredient_with_stock.ingredient_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["current_stock"] == pytest.approx(500.0)


def test_get_ingredient_not_found(client: TestClient, admin_headers: dict, test_data):
    r = client.get("/api/v1/admin/ingredients/99999", headers=admin_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /ingredients/{id}
# ---------------------------------------------------------------------------


def test_patch_ingredient_success(
    client: TestClient, admin_headers: dict, active_ingredient, test_data
):
    r = client.patch(
        f"/api/v1/admin/ingredients/{active_ingredient.ingredient_id}",
        headers=admin_headers,
        json={
            "name": "Café especial",
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Café especial"


def test_patch_ingredient_not_found(client: TestClient, admin_headers: dict, test_data):
    r = client.patch("/api/v1/admin/ingredients/99999", headers=admin_headers, json={"name": "X"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /ingredients/adjustments
# ---------------------------------------------------------------------------


def test_adjustment_positive_in(
    client: TestClient, admin_headers: dict, active_ingredient, test_data
):
    r = client.post(
        "/api/v1/admin/ingredients/adjustments",
        headers=admin_headers,
        json={
            "ingredient_id": active_ingredient.ingredient_id,
            "quantity": 100.0,
            "reason": "RECEIPT",
        },
    )
    assert r.status_code == 200
    assert r.json()["new_stock"] == pytest.approx(100.0)


def test_adjustment_negative_out(
    client: TestClient, admin_headers: dict, ingredient_with_stock, test_data
):
    r = client.post(
        "/api/v1/admin/ingredients/adjustments",
        headers=admin_headers,
        json={
            "ingredient_id": ingredient_with_stock.ingredient_id,
            "quantity": -100.0,
            "reason": "WASTE",
        },
    )
    assert r.status_code == 200
    assert r.json()["new_stock"] == pytest.approx(400.0)


def test_adjustment_insufficient_stock_returns_400(
    client: TestClient, admin_headers: dict, active_ingredient, test_data
):
    r = client.post(
        "/api/v1/admin/ingredients/adjustments",
        headers=admin_headers,
        json={
            "ingredient_id": active_ingredient.ingredient_id,
            "quantity": -999.0,
            "reason": "WASTE",
        },
    )
    assert r.status_code == 400


def test_adjustment_not_found_returns_404(client: TestClient, admin_headers: dict, test_data):
    r = client.post(
        "/api/v1/admin/ingredients/adjustments",
        headers=admin_headers,
        json={
            "ingredient_id": 99999,
            "quantity": 10.0,
            "reason": "RECEIPT",
        },
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /ingredients/products/{id}/consumption
# ---------------------------------------------------------------------------


def test_get_consumption_empty(
    client: TestClient, admin_headers: dict, product_for_recipe, test_data
):
    r = client.get(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


def test_get_consumption_with_recipe(
    client: TestClient,
    admin_headers: dict,
    product_for_recipe,
    ingredient_with_stock,
    test_data,
):
    # Set recipe first
    client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={
            "items": [
                {
                    "ingredient_id": ingredient_with_stock.ingredient_id,
                    "quantity_used": 10.0,
                }
            ]
        },
    )
    r = client.get(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["ingredient_id"] == ingredient_with_stock.ingredient_id


# ---------------------------------------------------------------------------
# POST /ingredients/products/{id}/consumption
# ---------------------------------------------------------------------------


def test_upsert_consumption_replaces_recipe(
    client: TestClient,
    admin_headers: dict,
    product_for_recipe,
    ingredient_with_stock,
    test_data,
):
    r = client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={
            "items": [
                {
                    "ingredient_id": ingredient_with_stock.ingredient_id,
                    "quantity_used": 5.0,
                }
            ]
        },
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_upsert_consumption_empty_clears_recipe(
    client: TestClient,
    admin_headers: dict,
    product_for_recipe,
    ingredient_with_stock,
    test_data,
):
    # First set a recipe
    client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={
            "items": [
                {
                    "ingredient_id": ingredient_with_stock.ingredient_id,
                    "quantity_used": 5.0,
                }
            ]
        },
    )
    # Then clear it
    r = client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={"items": []},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_upsert_consumption_inactive_ingredient_returns_400(
    client: TestClient,
    admin_headers: dict,
    product_for_recipe,
    inactive_ingredient,
    test_data,
):
    r = client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={
            "items": [
                {
                    "ingredient_id": inactive_ingredient.ingredient_id,
                    "quantity_used": 5.0,
                }
            ]
        },
    )
    assert r.status_code == 400


def test_upsert_consumption_product_not_found_returns_404(
    client: TestClient, admin_headers: dict, active_ingredient, test_data
):
    r = client.post(
        "/api/v1/admin/ingredients/products/99999/consumption",
        headers=admin_headers,
        json={"items": [{"ingredient_id": active_ingredient.ingredient_id, "quantity_used": 5.0}]},
    )
    assert r.status_code == 404


def test_upsert_consumption_zero_quantity_returns_422(
    client: TestClient,
    admin_headers: dict,
    product_for_recipe,
    active_ingredient,
    test_data,
):
    """quantity_used <= 0 is rejected by Pydantic validator → 422."""
    r = client.post(
        f"/api/v1/admin/ingredients/products/{product_for_recipe.product_id}/consumption",
        headers=admin_headers,
        json={"items": [{"ingredient_id": active_ingredient.ingredient_id, "quantity_used": 0}]},
    )
    assert r.status_code == 422
