# Implementation Plan: backend-unit-test-coverage

## Overview

Elevate the CoffeeAndChill backend (FastAPI + Python 3.11) unit test coverage from 68.93% to above the 80% SonarQube threshold by creating a structured test suite split into pure unit tests (`tests/unit/`) and integration tests (`tests/integration/`). The plan covers security utilities, fulfillment logic, availability services, and five router modules (employees, ingredients, products, payments, inventory).

## Tasks

- [x] 1. Set up test suite directory structure and shared fixtures
  - Create `tests/unit/__init__.py` and `tests/integration/__init__.py`
  - Verify that `tests/conftest.py` exposes `client`, `session`, and `test_data` fixtures with `function` scope backed by an in-memory SQLite database and `fakeredis`
  - Add `hypothesis` to project dependencies (`pip install hypothesis`) for property-based tests
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 2. Implement unit tests for `app/core/security.py`
  - [x] 2.1 Write unit tests for `hash_password` and `verify_password`
    - Test that `hash_password` returns a non-empty string different from the input
    - Test that two calls with the same input produce distinct hashes (bcrypt salt)
    - Test that `verify_password` returns `True` for a matching plain-text/hash pair and `False` for a non-matching pair
    - Create `tests/unit/test_core_security.py`; no DB or HTTP client imports allowed
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 Write property test for hash non-emptiness and non-determinism (Property 1)
    - **Property 1: Hash non-emptiness and non-determinism**
    - **Validates: Requirements 2.1, 2.2**
    - Use `hypothesis` `@given(st.text(min_size=1))` to assert `hash_password` always returns a non-empty string different from the input and that two successive calls differ

  - [ ]* 2.3 Write property test for password verification round-trip (Property 2)
    - **Property 2: Password verification round-trip**
    - **Validates: Requirements 2.3, 2.4**
    - Use `hypothesis` `@given(st.text(min_size=1), st.text(min_size=1))` to assert `verify_password(plain, hash_password(plain))` is `True` and `verify_password(other, hash_password(plain))` is `False` when `other != plain`

  - [x] 2.4 Write unit tests for `create_access_token`, `create_refresh_token`, and `decode_token`
    - Use `@pytest.mark.parametrize` with several `(user_id, role)` pairs
    - Assert decoded payload contains `sub == str(user_id)`, `role`, `type == "access"` / `"refresh"`, `jti`, `iat`, `exp`
    - Assert refresh token `exp` is strictly greater than access token `exp` for the same arguments
    - Assert `decode_token` returns `None` for malformed, tampered, and expired tokens
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

  - [ ]* 2.5 Write property test for JWT creation and decoding round-trip (Property 3)
    - **Property 3: JWT creation and decoding round-trip**
    - **Validates: Requirements 2.5, 2.6, 2.7**
    - Use `hypothesis` `@given(st.integers(min_value=1), st.text(min_size=1, max_size=50))` to assert that `decode_token(create_access_token(uid, role))` always returns a dict with the original `sub`, `role`, and `type` claims

  - [ ]* 2.6 Write property test for invalid token decoding returns None (Property 4)
    - **Property 4: Invalid token decoding returns None**
    - **Validates: Requirements 2.8**
    - Use `hypothesis` `@given(st.text())` to assert that `decode_token` returns `None` for arbitrary strings that are not valid JWTs produced by the Security_Module

- [x] 3. Implement unit tests for `app/core/fulfillment.py`
  - [x] 3.1 Write unit tests for `resolve_effective_fulfillment`
    - Use `@pytest.mark.parametrize` to cover all six combinations of `FulfillmentType` × `has_recipe`
    - Test the invalid-input edge case (non-enum string) and assert `ValueError` or `"STOCK"` default
    - Create `tests/unit/test_core_fulfillment.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.2 Write property test for fulfillment resolution matrix (Property 5)
    - **Property 5: Fulfillment resolution matrix**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    - Use `hypothesis` `@given(st.sampled_from(["STOCK", "INGREDIENTS", "BOTH"]), st.booleans())` to assert the full decision matrix holds for all generated combinations

- [x] 4. Implement unit tests for `app/services/availability.py`
  - [x] 4.1 Write unit tests for `should_decrement_product_stock` and `should_record_product_inventory_movement`
    - Use `@pytest.mark.parametrize` to cover all combinations of `FulfillmentType` × `has_recipe` for both functions
    - Create `tests/unit/test_services_availability.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 4.2 Write property test for stock decrement and inventory movement decision matrix (Property 6)
    - **Property 6: Stock decrement and inventory movement decision matrix**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**
    - Use `hypothesis` `@given(st.sampled_from(["STOCK", "INGREDIENTS", "BOTH"]), st.booleans())` to assert both functions return the correct boolean for all generated combinations

  - [x] 4.3 Write unit tests for `get_product_cupo_by_stock_field`
    - Test positive `stock_quantity` returns that value; `0` returns `0`; `None` returns `0`; negative integer returns `0`
    - _Requirements: 4.7, 4.8, 4.9, 4.10_

  - [ ]* 4.4 Write property test for cupo is never negative (Property 7)
    - **Property 7: Cupo is never negative**
    - **Validates: Requirements 4.9, 4.10**
    - Use `hypothesis` `@given(st.one_of(st.integers(), st.none()))` to assert `get_product_cupo_by_stock_field` always returns a value `>= 0` for any `stock_quantity`

- [x] 5. Checkpoint — Ensure all unit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement integration tests for `app/routers/employees.py`
  - [-] 6.1 Write integration tests for `GET /admin/employees` and `POST /admin/employees`
    - Add `admin_headers` and `employee_headers` fixtures (local to `tests/integration/test_employees.py`)
    - Test list returns HTTP 200 with required fields; test successful creation returns HTTP 201 with `is_active=True`
    - Test duplicate email returns HTTP 409; test invalid role returns HTTP 400
    - Test missing/unauthorized token returns HTTP 403
    - Create `tests/integration/test_employees.py`
    - _Requirements: 5.1, 5.2, 5.3, 5.10, 5.11_

  - [-] 6.2 Write integration tests for `PUT /admin/employees/{id}` and `PATCH /admin/employees/{id}/status`
    - Test partial update returns HTTP 200 with updated fields
    - Test non-existent employee returns HTTP 404; duplicate email returns HTTP 409
    - Test status toggle returns HTTP 200 with updated `is_active`
    - Test self-deactivation returns HTTP 400; non-existent employee returns HTTP 404
    - _Requirements: 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [ ] 7. Implement integration tests for `app/routers/ingredients.py`
  - [-] 7.1 Write integration tests for ingredient CRUD endpoints
    - Test `GET /ingredients` returns only active ingredients; with `active_only=false` includes inactive
    - Test `POST /ingredients` returns HTTP 201 with `current_stock == 0`
    - Test `GET /ingredients/{id}` returns stock calculated from movements; non-existent returns HTTP 404
    - Test `PATCH /ingredients/{id}` partial update; non-existent returns HTTP 404
    - Create `tests/integration/test_ingredients.py` with `ingredient_with_stock` fixture
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [-] 7.2 Write integration tests for ingredient stock adjustments
    - Test positive quantity returns HTTP 200 with `movement_type == "IN"`
    - Test negative quantity within stock returns HTTP 200 with `movement_type == "OUT"`
    - Test negative quantity exceeding stock returns HTTP 400
    - Test non-existent ingredient returns HTTP 404
    - _Requirements: 6.8, 6.9, 6.10, 6.11_

  - [-] 7.3 Write integration tests for recipe (consumption) management
    - Test `GET /ingredients/products/{id}/consumption` returns empty list for product with no recipe
    - Test returns consumption items for product with recipe
    - Test `POST /ingredients/products/{id}/consumption` replaces existing recipe; empty list deletes recipe
    - Test inactive ingredient returns HTTP 400; non-existent product returns HTTP 404; `quantity_used <= 0` returns HTTP 400
    - _Requirements: 6.12, 6.13, 6.14, 6.15, 6.16, 6.17, 6.18_

- [ ] 8. Implement integration tests for `app/routers/products.py`
  - [-] 8.1 Write integration tests for `POST /products` and `PATCH /products/{id}`
    - Test successful creation returns HTTP 201 with required fields
    - Test `price <= 0` returns HTTP 400; `stock_quantity < 0` returns HTTP 400; invalid `category_id` returns HTTP 404; invalid `fulfillment_type` returns HTTP 400
    - Test partial update returns HTTP 200; non-existent product returns HTTP 404; invalid price/stock/category/fulfillment_type return correct error codes
    - Create `tests/integration/test_products.py`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11_

  - [-] 8.2 Write integration tests for `PATCH /products/{id}/status` and `POST /products/upload-image`
    - Test status change to `ACTIVE`/`INACTIVE` returns HTTP 200 with updated `status`
    - Test invalid status value returns HTTP 400; non-existent product returns HTTP 404
    - Test valid MIME type upload returns HTTP 200 with non-empty `image_url` (mock filesystem with `unittest.mock.patch`)
    - Test invalid MIME type returns HTTP 400; file > 5 MB returns HTTP 400
    - _Requirements: 7.12, 7.13, 7.14, 7.15, 7.16, 7.17_

- [ ] 9. Implement integration tests for `app/routers/payments.py`
  - [-] 9.1 Write integration tests for `GET /payments`
    - Test empty DB returns HTTP 200 with empty `payments` list and all summary fields equal to `0`
    - Test with seeded payments returns `count` matching seeded count and all totals `> 0`
    - Test valid `date` filter returns only payments matching that date
    - Test invalid date format defaults to today's date
    - Test `limit`/`offset` pagination: `limit=N` returns at most N items; offset beyond total returns empty list
    - Assert response always contains `payments`, `count`, `total_ventas`, `total_propinas`, `total_con_propinas`
    - Create `tests/integration/test_payments.py`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 10. Implement integration tests for `app/routers/inventory.py`
  - [-] 10.1 Write integration tests for `GET /inventory`
    - Test pagination: `page=1&limit=N` returns at most N items; page beyond last returns empty list
    - Test `category_id` filter returns only matching products
    - Test `low_stock_count` equals number of products with `stock < min_stock`
    - Create `tests/integration/test_inventory.py`
    - _Requirements: 9.1, 9.2, 9.3_

  - [-] 10.2 Write integration tests for `POST /inventory/adjustments`
    - Test positive quantity returns HTTP 200 with `movement_type == "IN"`
    - Test negative quantity within stock returns HTTP 200 with `movement_type == "OUT"`
    - Test negative quantity exceeding stock returns HTTP 400
    - Test non-existent product returns HTTP 404
    - _Requirements: 9.4, 9.5, 9.6, 9.7_

  - [ ] 10.3 Write integration tests for `GET /inventory/movements`
    - Test without filters returns all movements
    - Test `movement_type` filter returns only matching movements
    - Test `product_id` filter returns only matching movements
    - Test `start_date`/`end_date` filters return only movements within the inclusive range
    - Test `limit`/`page` pagination applies correctly
    - _Requirements: 9.8, 9.9, 9.10, 9.11, 9.12_

- [~] 11. Checkpoint — Ensure all integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Enforce coverage threshold and generate coverage report
  - [~] 12.1 Verify pytest-cov configuration and coverage threshold
    - Confirm `pytest tests/ --cov=app --cov-fail-under=80 --cov-report=xml:coverage.xml --cov-report=term-missing` exits with code 0
    - Confirm `coverage.xml` is generated in the project root in Cobertura XML format
    - Confirm running only `pytest tests/unit/` achieves 100% line coverage for `app/core/security.py`, `app/core/fulfillment.py`, and the three pure functions in `app/services/availability.py`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [~] 13. Final checkpoint — Ensure all tests pass and coverage threshold is met
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Unit tests in `tests/unit/` must never import `TestClient`, database engines, or session objects
- Integration tests in `tests/integration/` must consume `client`, `session`, and `test_data` exclusively from `tests/conftest.py`
- Property tests use `hypothesis`; install with `pip install hypothesis` before running
- Checkpoints ensure incremental validation after each major layer

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "4.3"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.2", "4.2", "4.4"] },
    { "id": 3, "tasks": ["2.5", "2.6", "6.1", "7.1", "8.1", "9.1", "10.1"] },
    { "id": 4, "tasks": ["6.2", "7.2", "8.2", "10.2"] },
    { "id": 5, "tasks": ["7.3", "10.3"] },
    { "id": 6, "tasks": ["12.1"] }
  ]
}
```
