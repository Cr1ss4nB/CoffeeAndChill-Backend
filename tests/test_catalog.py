from fastapi.testclient import TestClient


def test_get_categories_empty(client: TestClient):
    response = client.get("/catalog/categories")
    assert response.status_code == 200
    assert response.json() == []


def test_get_products_empty(client: TestClient):
    response = client.get("/catalog/products")
    assert response.status_code == 200
    assert response.json() == []


def test_get_product_not_found(client: TestClient):
    response = client.get("/catalog/products/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Producto no encontrado"


def test_catalog_with_data(client: TestClient, session):
    from app.models.catalog import Category, Product

    cat = Category(category_name="Cat Test", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    prod = Product(name="Prod Test", category_id=cat.category_id, price=100.0, stock_quantity=10)
    session.add(prod)
    session.commit()
    session.refresh(prod)

    # Test get category
    resp_cat = client.get("/catalog/categories")
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()) == 1
    assert resp_cat.json()[0]["category_name"] == "Cat Test"

    # Test get products
    resp_prod = client.get("/catalog/products")
    assert resp_prod.status_code == 200
    assert len(resp_prod.json()) == 1
    assert resp_prod.json()[0]["name"] == "Prod Test"

    # Test get product specific
    resp_detail = client.get(f"/catalog/products/{prod.product_id}")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["name"] == "Prod Test"
    assert resp_detail.json()["category"]["category_name"] == "Cat Test"
