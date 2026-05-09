"""
Regresiones de catálogo.
P0 additions: active_only flag, filter by category_id.
"""
from fastapi.testclient import TestClient
from sqlmodel import Session

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

    prod = Product(
        name="Prod Test",
        category_id=cat.category_id,
        price=100.0,
        stock_quantity=10,
        fulfillment_type="STOCK",
    )
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
    row = resp_prod.json()[0]
    assert row["name"] == "Prod Test"
    assert row["available_to_sell"] == 10
    assert row["fulfillment_type"] == "STOCK"

    # Test get product specific
    resp_detail = client.get(f"/catalog/products/{prod.product_id}")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["name"] == "Prod Test"
    assert resp_detail.json()["category"]["category_name"] == "Cat Test"

def test_catalog_products_default_excludes_inactive(client: TestClient, session: Session):
    from app.models.catalog import Category, Product

    cat = Category(category_name="Reg Cat", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    active = Product(name="Activo", category_id=cat.category_id, price=100.0, stock_quantity=5, status="ACTIVE")
    inactive = Product(name="Inactivo", category_id=cat.category_id, price=100.0, stock_quantity=5, status="INACTIVE")
    session.add(active)
    session.add(inactive)
    session.commit()

    r = client.get("/catalog/products")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Activo" in names
    assert "Inactivo" not in names

def test_catalog_products_active_only_false_includes_inactive(
    client: TestClient, session: Session
):
    """GET /catalog/products?active_only=false DEBE incluir productos INACTIVE."""
    from app.models.catalog import Category, Product

    cat = Category(category_name="Reg Cat2", type="PRODUCT")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    active = Product(name="Activo2", category_id=cat.category_id, price=100.0, stock_quantity=5, status="ACTIVE")
    inactive = Product(name="Inactivo2", category_id=cat.category_id, price=100.0, stock_quantity=5, status="INACTIVE")
    session.add(active)
    session.add(inactive)
    session.commit()

    r = client.get("/catalog/products?active_only=false")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Activo2" in names
    assert "Inactivo2" in names

def test_catalog_products_filter_by_category(client: TestClient, session: Session):
    """category_id query param filtra por categoría correctamente."""
    from app.models.catalog import Category, Product

    cat_a = Category(category_name="Bebidas", type="PRODUCT")
    cat_b = Category(category_name="Comida", type="PRODUCT")
    session.add(cat_a)
    session.add(cat_b)
    session.commit()
    session.refresh(cat_a)
    session.refresh(cat_b)

    session.add(Product(name="Café", category_id=cat_a.category_id, price=100.0, stock_quantity=5))
    session.add(Product(name="Tostada", category_id=cat_b.category_id, price=200.0, stock_quantity=5))
    session.commit()

    r = client.get(f"/catalog/products?category_id={cat_a.category_id}")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Café" in names
    assert "Tostada" not in names

def test_catalog_categories_active_only_false_includes_inactive(
    client: TestClient, session: Session
):
    """GET /catalog/categories?active_only=false incluye categorías inactivas."""
    from app.models.catalog import Category

    active_cat = Category(category_name="Activa", type="PRODUCT", is_active=True)
    inactive_cat = Category(category_name="Inactiva", type="PRODUCT", is_active=False)
    session.add(active_cat)
    session.add(inactive_cat)
    session.commit()

    r_default = client.get("/catalog/categories")
    default_names = [c["category_name"] for c in r_default.json()]
    assert "Activa" in default_names
    assert "Inactiva" not in default_names

    r_all = client.get("/catalog/categories?active_only=false")
    all_names = [c["category_name"] for c in r_all.json()]
    assert "Activa" in all_names
    assert "Inactiva" in all_names