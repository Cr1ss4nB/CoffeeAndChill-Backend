from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.catalog import Category, Product
from app.models.inventory import Ingredient, IngredientStockMovement, ProductConsumption
from tests.conftest import get_admin_headers


def test_list_ingredients_empty(client: TestClient, test_data):
    headers = get_admin_headers(client)
    response = client.get("/api/v1/admin/ingredients", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_ingredient_success(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)
    payload = {
        "name": "Café en grano",
        "unit": "g",
        "description": "Granos de café de especialidad",
        "min_stock": 500.0,
    }
    response = client.post("/api/v1/admin/ingredients", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["unit"] == payload["unit"]
    assert data["min_stock"] == payload["min_stock"]
    assert data["current_stock"] == 0.0

    # Verify db
    db_ing = session.exec(select(Ingredient).where(Ingredient.name == "Café en grano")).first()
    assert db_ing is not None


def test_create_ingredient_requires_auth(client: TestClient):
    payload = {
        "name": "Café en grano",
        "unit": "g",
        "min_stock": 500.0,
    }
    response = client.post("/api/v1/admin/ingredients", json=payload)
    assert response.status_code == 403


def test_get_ingredient(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)
    ing = Ingredient(name="Leche entera", unit="l", min_stock=10.0)
    session.add(ing)
    session.commit()
    session.refresh(ing)

    # Success
    response = client.get(f"/api/v1/admin/ingredients/{ing.ingredient_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Leche entera"

    # Not found
    response_nf = client.get("/api/v1/admin/ingredients/9999", headers=headers)
    assert response_nf.status_code == 404


def test_update_ingredient(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)
    ing = Ingredient(name="Azúcar", unit="kg", min_stock=5.0)
    session.add(ing)
    session.commit()
    session.refresh(ing)

    payload = {"name": "Azúcar Blanca", "min_stock": 8.0}
    response = client.patch(
        f"/api/v1/admin/ingredients/{ing.ingredient_id}", headers=headers, json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Azúcar Blanca"
    assert data["min_stock"] == 8.0

    # Not found
    response_nf = client.patch("/api/v1/admin/ingredients/9999", headers=headers, json=payload)
    assert response_nf.status_code == 404


def test_adjust_ingredient_stock(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)
    ing = Ingredient(name="Menta", unit="g", min_stock=50.0)
    session.add(ing)
    session.commit()
    session.refresh(ing)

    # Positive adjustment (IN)
    payload_in = {
        "ingredient_id": ing.ingredient_id,
        "quantity": 100.0,
        "reason": "RECEIPT",
        "notes": "Compra semanal",
    }
    resp_in = client.post("/api/v1/admin/ingredients/adjustments", headers=headers, json=payload_in)
    assert resp_in.status_code == 200
    assert resp_in.json()["new_stock"] == 100.0

    # Negative adjustment (OUT)
    payload_out = {
        "ingredient_id": ing.ingredient_id,
        "quantity": -30.0,
        "reason": "WASTE",
        "notes": "Hojas dañadas",
    }
    resp_out = client.post(
        "/api/v1/admin/ingredients/adjustments", headers=headers, json=payload_out
    )
    assert resp_out.status_code == 200
    assert resp_out.json()["new_stock"] == 70.0

    # Insufficient stock error
    payload_insufficient = {
        "ingredient_id": ing.ingredient_id,
        "quantity": -80.0,
        "reason": "WASTE",
    }
    resp_err = client.post(
        "/api/v1/admin/ingredients/adjustments", headers=headers, json=payload_insufficient
    )
    assert resp_err.status_code == 400
    assert "Stock insuficiente" in resp_err.json()["detail"]

    # Not found
    payload_nf = {
        "ingredient_id": 9999,
        "quantity": 10.0,
        "reason": "RECEIPT",
    }
    resp_nf = client.post("/api/v1/admin/ingredients/adjustments", headers=headers, json=payload_nf)
    assert resp_nf.status_code == 404


def test_product_recipe_consumption(client: TestClient, session: Session, test_data):
    headers = get_admin_headers(client)

    # Seed an ingredient
    ing = Ingredient(name="Cacao", unit="g", min_stock=200.0)
    session.add(ing)
    session.commit()
    session.refresh(ing)

    # Seed a category and a product
    cat = Category(category_name="Cat Test", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    prod = Product(
        name="Mocaccino",
        category_id=cat.category_id,
        price=120.0,
        stock_quantity=10,
        fulfillment_type="STOCK",
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # GET empty recipe
    resp_get = client.get(
        f"/api/v1/admin/ingredients/products/{prod.product_id}/consumption", headers=headers
    )
    assert resp_get.status_code == 200
    assert resp_get.json() == []

    # POST upsert recipe
    payload = {
        "items": [
            {"ingredient_id": ing.ingredient_id, "quantity_used": 15.0}
        ]
    }
    resp_post = client.post(
        f"/api/v1/admin/ingredients/products/{prod.product_id}/consumption",
        headers=headers,
        json=payload,
    )
    assert resp_post.status_code == 200
    data = resp_post.json()
    assert len(data) == 1
    assert data[0]["ingredient_id"] == ing.ingredient_id
    assert data[0]["quantity_used"] == 15.0

    # Verify get again
    resp_get2 = client.get(
        f"/api/v1/admin/ingredients/products/{prod.product_id}/consumption", headers=headers
    )
    assert len(resp_get2.json()) == 1

    # POST validation: product not found
    resp_pnf = client.post(
        "/api/v1/admin/ingredients/products/9999/consumption",
        headers=headers,
        json=payload,
    )
    assert resp_pnf.status_code == 404

    # POST validation: ingredient not active
    ing.is_active = False
    session.add(ing)
    session.commit()
    resp_err = client.post(
        f"/api/v1/admin/ingredients/products/{prod.product_id}/consumption",
        headers=headers,
        json=payload,
    )
    assert resp_err.status_code == 400
    assert "Insumo inactivo" in resp_err.json()["detail"]

    # POST validation: ingredient not found
    payload_inf = {
        "items": [
            {"ingredient_id": 9999, "quantity_used": 15.0}
        ]
    }
    resp_inf = client.post(
        f"/api/v1/admin/ingredients/products/{prod.product_id}/consumption",
        headers=headers,
        json=payload_inf,
    )
    assert resp_inf.status_code == 404
