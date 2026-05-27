# Requirements Document

## Introduction

This document defines the requirements for elevating the unit test coverage of the CoffeeAndChill backend (FastAPI + Python 3.11) from the current 68.93% (1216/1764 lines) to above the 80% threshold enforced by SonarQube. The feature involves creating a structured test suite — split into pure unit tests and integration tests — that covers the untested modules with the highest business-logic density: security utilities, fulfillment logic, availability services, and five router modules (employees, ingredients, products, payments, inventory).

## Glossary

- **Test_Suite**: The complete collection of automated tests under the `tests/` directory, including both `unit/` and `integration/` subdirectories.
- **Security_Module**: The module `app/core/security.py`, which provides password hashing, JWT creation, and JWT decoding functions.
- **Fulfillment_Module**: The module `app/core/fulfillment.py`, which resolves the effective fulfillment type for a product.
- **Availability_Service**: The module `app/services/availability.py`, which provides pure functions to determine stock decrement and cupo logic.
- **Employees_Router**: The FastAPI router at `app/routers/employees.py`, which handles CRUD operations and status management for system users.
- **Ingredients_Router**: The FastAPI router at `app/routers/ingredients.py`, which handles CRUD operations, stock adjustments, and recipe management for ingredients.
- **Products_Router**: The FastAPI router at `app/routers/products.py`, which handles CRUD operations, status changes, and image uploads for products.
- **Payments_Router**: The FastAPI router at `app/routers/payments.py`, which handles payment history queries with date filtering and pagination.
- **Inventory_Router**: The FastAPI router at `app/routers/inventory.py`, which handles paginated inventory queries, stock adjustments, and movement history.
- **Coverage_Tool**: The `pytest-cov` plugin used to measure and report line coverage, configured via `--cov=app --cov-fail-under=80`.
- **FulfillmentType**: An enumeration with values `STOCK`, `INGREDIENTS`, and `BOTH`, representing how a product's availability is tracked.
- **conftest.py**: The existing pytest configuration file that provides the `client`, `session`, and `test_data` fixtures backed by an in-memory SQLite database and `fakeredis`.

---

## Requirements

### Requirement 1: Test Suite Structure

**User Story:** As a developer, I want a clearly organized test suite with separate directories for unit and integration tests, so that I can run fast pure-logic tests independently from database-backed integration tests.

#### Acceptance Criteria

1. THE Test_Suite SHALL contain a `tests/unit/` directory with an `__init__.py` file; every test file placed in that directory SHALL NOT import any HTTP client, database engine, or database session object.
2. THE Test_Suite SHALL contain a `tests/integration/` directory with an `__init__.py` file for tests that interact with the application via `TestClient` and an in-memory SQLite database.
3. WHEN unit tests are executed via `pytest tests/unit/`, THE Test_Suite SHALL complete the entire `tests/unit/` suite in under 5 seconds without requiring any database connection or HTTP server.
4. WHEN integration tests are executed, THE Test_Suite SHALL obtain the `client`, `session`, and `test_data` fixtures exclusively from the `conftest.py` file at the `tests/` root; no integration test file SHALL redeclare those fixtures locally.
5. THE `conftest.py` file SHALL be located at `tests/conftest.py` and SHALL define the `client`, `session`, and `test_data` fixtures with `function` scope so that each test receives a fresh database state.

---

### Requirement 2: Security Module Unit Tests

**User Story:** As a developer, I want complete unit test coverage for `app/core/security.py`, so that I can verify that password hashing, token creation, and token decoding behave correctly for all valid and invalid inputs.

#### Acceptance Criteria

1. WHEN `hash_password` is called with any non-empty string, THE Security_Module SHALL return a non-empty string that is not equal to the original input.
2. WHEN `hash_password` is called twice with the same input string, THE Security_Module SHALL return two distinct hash strings (non-deterministic due to bcrypt salt).
3. WHEN `verify_password` is called with a plain-text password and the hash produced by `hash_password` for that same password, THE Security_Module SHALL return `True`.
4. WHEN `verify_password` is called with a plain-text password that does not match the original password used to produce the hash, THE Security_Module SHALL return `False`.
5. WHEN `create_access_token` is called with a `user_id` that is a positive integer and a `role` that is a non-empty string of at most 50 characters, THE Security_Module SHALL return a JWT whose decoded payload contains `sub` equal to `str(user_id)`, `role` equal to the provided role, and `type` equal to `"access"`.
6. WHEN `create_refresh_token` is called with a valid `user_id` and `role`, THE Security_Module SHALL return a JWT whose decoded payload contains `sub` equal to `str(user_id)`, `role` equal to the provided role, `type` equal to `"refresh"`, and an `exp` timestamp strictly greater than the `exp` of the corresponding access token created with the same arguments.
7. WHEN `decode_token` is called with a JWT previously produced by `create_access_token` or `create_refresh_token`, THE Security_Module SHALL return a dictionary containing at minimum the keys `sub`, `role`, `type`, `jti`, `iat`, and `exp` with the values used at creation time.
8. IF `decode_token` is called with a string that is not a valid JWT, has been tampered with, was signed with a different key, or has expired, THEN THE Security_Module SHALL return `None`.

---

### Requirement 3: Fulfillment Module Unit Tests

**User Story:** As a developer, I want complete unit test coverage for `app/core/fulfillment.py`, so that I can verify that the effective fulfillment type is resolved correctly for every combination of FulfillmentType and recipe presence.

#### Acceptance Criteria

1. WHEN `resolve_effective_fulfillment` is called with `FulfillmentType.STOCK`, `FulfillmentType.INGREDIENTS`, or `FulfillmentType.BOTH` and `has_recipe=False`, THE Fulfillment_Module SHALL return `"STOCK"` in all three cases.
2. WHEN `resolve_effective_fulfillment` is called with `FulfillmentType.STOCK` and `has_recipe=True`, THE Fulfillment_Module SHALL return `"STOCK"`.
3. WHEN `resolve_effective_fulfillment` is called with `FulfillmentType.INGREDIENTS` and `has_recipe=True`, THE Fulfillment_Module SHALL return `"INGREDIENTS"`.
4. WHEN `resolve_effective_fulfillment` is called with `FulfillmentType.BOTH` and `has_recipe=True`, THE Fulfillment_Module SHALL return `"BOTH"`.
5. IF `resolve_effective_fulfillment` is called with a string value that is not one of `"STOCK"`, `"INGREDIENTS"`, or `"BOTH"`, THEN THE Fulfillment_Module SHALL raise a `ValueError` or return `"STOCK"` as a safe default, and this behavior SHALL be explicitly tested.

---

### Requirement 4: Availability Service Unit Tests

**User Story:** As a developer, I want complete unit test coverage for the pure functions in `app/services/availability.py`, so that I can verify that stock decrement decisions and cupo calculations are correct for all input combinations.

#### Acceptance Criteria

1. WHEN `should_decrement_product_stock` is called with `FulfillmentType.STOCK`, `FulfillmentType.INGREDIENTS`, or `FulfillmentType.BOTH` and `has_recipe=False`, THE Availability_Service SHALL return `True` for all three cases.
2. WHEN `should_decrement_product_stock` is called with `FulfillmentType.INGREDIENTS` and `has_recipe=True`, THE Availability_Service SHALL return `False`.
3. WHEN `should_decrement_product_stock` is called with `FulfillmentType.STOCK` and `has_recipe=True`, THE Availability_Service SHALL return `True`.
4. WHEN `should_decrement_product_stock` is called with `FulfillmentType.BOTH` and `has_recipe=True`, THE Availability_Service SHALL return `True`.
5. WHEN `should_record_product_inventory_movement` is called with `FulfillmentType.STOCK`, `FulfillmentType.INGREDIENTS`, or `FulfillmentType.BOTH` and `has_recipe=False`, THE Availability_Service SHALL return `True` for all three cases.
6. WHEN `should_record_product_inventory_movement` is called with `FulfillmentType.INGREDIENTS` and `has_recipe=True`, THE Availability_Service SHALL return `False`.
7. WHEN `should_record_product_inventory_movement` is called with `FulfillmentType.STOCK` and `has_recipe=True`, THE Availability_Service SHALL return `True`.
8. WHEN `should_record_product_inventory_movement` is called with `FulfillmentType.BOTH` and `has_recipe=True`, THE Availability_Service SHALL return `True`.
9. WHEN `get_product_cupo_by_stock_field` is called with a product whose `stock_quantity` is a positive integer, THE Availability_Service SHALL return that integer value.
10. IF `get_product_cupo_by_stock_field` is called with a product whose `stock_quantity` is `0`, `None`, or a negative integer, THEN THE Availability_Service SHALL return `0`.

---

### Requirement 5: Employees Router Integration Tests

**User Story:** As a developer, I want integration tests for `app/routers/employees.py`, so that I can verify that employee CRUD operations and status management enforce business rules and authorization correctly.

#### Acceptance Criteria

1. WHEN `GET /admin/employees` is called with a valid admin Bearer token, THE Employees_Router SHALL return HTTP 200 and a JSON array where each element contains at minimum `employee_id`, `full_name`, `email`, `role`, and `is_active`.
2. WHEN `POST /admin/employees` is called with a JSON body containing `full_name`, `email`, `password`, and `role` (one of `admin`, `waiter`, or `cashier`) and a valid admin Bearer token, THE Employees_Router SHALL return HTTP 201 and a JSON object containing the created employee's `email`, `role`, and `is_active=True`.
3. IF `POST /admin/employees` is called with an email address that already exists in the system, THEN THE Employees_Router SHALL return HTTP 409.
4. WHEN `PUT /admin/employees/{id}` is called with valid partial update data and a valid admin Bearer token, THE Employees_Router SHALL return HTTP 200 and a JSON object containing the updated `employee_id`, `full_name`, `email`, `role`, and `is_active`.
5. IF `PUT /admin/employees/{id}` is called with an email address already used by another employee, THEN THE Employees_Router SHALL return HTTP 409.
6. IF `PUT /admin/employees/{id}` is called with an `id` that does not correspond to any existing employee, THEN THE Employees_Router SHALL return HTTP 404.
7. WHEN `PATCH /admin/employees/{id}/status` is called to change an employee's active status with a valid admin Bearer token, THE Employees_Router SHALL return HTTP 200 and a JSON object containing the updated `employee_id` and `is_active` reflecting the new status.
8. IF `PATCH /admin/employees/{id}/status` is called to change the active status of the currently authenticated user's own account, THEN THE Employees_Router SHALL return HTTP 400.
9. IF `PATCH /admin/employees/{id}/status` is called with an `id` that does not correspond to any existing employee, THEN THE Employees_Router SHALL return HTTP 404.
10. IF any endpoint under `/admin/employees` is called without a Bearer token or with a token whose role does not have the `employees:manage` permission, THEN THE Employees_Router SHALL return HTTP 403.
11. IF `POST /admin/employees` is called with a `role` value that is not one of `admin`, `waiter`, or `cashier`, THEN THE Employees_Router SHALL return HTTP 400.

---

### Requirement 6: Ingredients Router Integration Tests

**User Story:** As a developer, I want integration tests for `app/routers/ingredients.py`, so that I can verify that ingredient CRUD, stock adjustments, and recipe management enforce business rules correctly.

#### Acceptance Criteria

1. WHEN `GET /ingredients` is called with a valid Bearer token, THE Ingredients_Router SHALL return HTTP 200 and a JSON array containing only ingredients whose `is_active` field is `True`.
2. WHEN `GET /ingredients` is called with `active_only=false` and a valid Bearer token, THE Ingredients_Router SHALL return HTTP 200 and a JSON array that includes both active and inactive ingredients.
3. WHEN `POST /ingredients` is called with valid ingredient data and a valid Bearer token with the required permission, THE Ingredients_Router SHALL return HTTP 201 and a JSON object representing the created ingredient with a `current_stock` field equal to `0`.
4. WHEN `GET /ingredients/{id}` is called with a valid ingredient ID and a valid Bearer token, THE Ingredients_Router SHALL return HTTP 200 and a JSON object that includes a `current_stock` field reflecting the sum of all recorded stock movements for that ingredient.
5. IF `GET /ingredients/{id}` is called with an ID that does not correspond to any ingredient, THEN THE Ingredients_Router SHALL return HTTP 404.
6. WHEN `PATCH /ingredients/{id}` is called with valid partial update data and a valid Bearer token with the required permission, THE Ingredients_Router SHALL return HTTP 200 and a JSON object reflecting the updated ingredient fields.
7. IF `PATCH /ingredients/{id}` is called with an ID that does not correspond to any ingredient, THEN THE Ingredients_Router SHALL return HTTP 404.
8. WHEN `POST /ingredients/adjustments` is called with a positive `quantity` and a valid Bearer token with the required permission, THE Ingredients_Router SHALL return HTTP 200 and a JSON object containing `movement_type` equal to `"IN"` and the `quantity` value used.
9. WHEN `POST /ingredients/adjustments` is called with a negative `quantity` whose absolute value does not exceed the current stock, THE Ingredients_Router SHALL return HTTP 200 and a JSON object containing `movement_type` equal to `"OUT"`.
10. IF `POST /ingredients/adjustments` is called with a negative `quantity` whose absolute value exceeds the current stock, THEN THE Ingredients_Router SHALL return HTTP 400.
11. IF `POST /ingredients/adjustments` is called with an ingredient ID that does not exist, THEN THE Ingredients_Router SHALL return HTTP 404.
12. WHEN `GET /ingredients/products/{id}/consumption` is called for a product with no recipe and a valid Bearer token, THE Ingredients_Router SHALL return HTTP 200 and an empty JSON array.
13. WHEN `GET /ingredients/products/{id}/consumption` is called for a product with a recipe and a valid Bearer token, THE Ingredients_Router SHALL return HTTP 200 and a JSON array of consumption items each containing `ingredient_id` and `quantity_used`.
14. WHEN `POST /ingredients/products/{id}/consumption` is called with a non-empty list of ingredient items (each with `ingredient_id` and `quantity_used > 0`) and a valid Bearer token, THE Ingredients_Router SHALL replace the existing recipe with the new list and return HTTP 200 with the updated consumption list.
15. WHEN `POST /ingredients/products/{id}/consumption` is called with an empty list and a valid Bearer token, THE Ingredients_Router SHALL delete all existing recipe entries for that product and return HTTP 200 with an empty list.
16. IF `POST /ingredients/products/{id}/consumption` is called with an ingredient whose `is_active` field is `False`, THEN THE Ingredients_Router SHALL return HTTP 400.
17. IF `POST /ingredients/products/{id}/consumption` is called with a product ID that does not exist, THEN THE Ingredients_Router SHALL return HTTP 404.
18. IF `POST /ingredients/products/{id}/consumption` is called with any item whose `quantity_used` is less than or equal to `0`, THEN THE Ingredients_Router SHALL return HTTP 400.

---

### Requirement 7: Products Router Integration Tests

**User Story:** As a developer, I want integration tests for `app/routers/products.py`, so that I can verify that product creation, updates, status changes, and image uploads enforce validation rules correctly.

#### Acceptance Criteria

1. WHEN `POST /products` is called with valid product data and a valid Bearer token with the required permission, THE Products_Router SHALL return HTTP 201 and a JSON object containing at minimum `product_id`, `name`, `price`, `stock_quantity`, `status`, and `fulfillment_type`.
2. IF `POST /products` is called with a `price` value less than or equal to `0`, THEN THE Products_Router SHALL return HTTP 400.
3. IF `POST /products` is called with a `stock_quantity` value less than `0`, THEN THE Products_Router SHALL return HTTP 400.
4. IF `POST /products` is called with a `category_id` that does not correspond to any existing category, THEN THE Products_Router SHALL return HTTP 404.
5. IF `POST /products` is called with a `fulfillment_type` value that is not one of `"STOCK"`, `"INGREDIENTS"`, or `"BOTH"`, THEN THE Products_Router SHALL return HTTP 400.
6. WHEN `PATCH /products/{id}` is called with valid partial update data and a valid Bearer token, THE Products_Router SHALL return HTTP 200 and a JSON object containing at minimum `product_id`, `name`, `price`, `stock_quantity`, `status`, and `fulfillment_type` reflecting the updated values.
7. IF `PATCH /products/{id}` is called with an ID that does not correspond to any existing product, THEN THE Products_Router SHALL return HTTP 404.
8. IF `PATCH /products/{id}` is called with a `price` value less than or equal to `0`, THEN THE Products_Router SHALL return HTTP 400.
9. IF `PATCH /products/{id}` is called with a `stock_quantity` value less than `0`, THEN THE Products_Router SHALL return HTTP 400.
10. IF `PATCH /products/{id}` is called with a `category_id` that does not correspond to any existing category, THEN THE Products_Router SHALL return HTTP 404.
11. IF `PATCH /products/{id}` is called with a `fulfillment_type` value that is not one of `"STOCK"`, `"INGREDIENTS"`, or `"BOTH"`, THEN THE Products_Router SHALL return HTTP 400.
12. WHEN `PATCH /products/{id}/status` is called with a valid status value (`ACTIVE` or `INACTIVE`) and a valid Bearer token, THE Products_Router SHALL return HTTP 200 and a JSON object containing at minimum `product_id`, `name`, `price`, `stock_quantity`, `status`, and `fulfillment_type` with `status` reflecting the new value.
13. IF `PATCH /products/{id}/status` is called with a status value other than `ACTIVE` or `INACTIVE`, THEN THE Products_Router SHALL return HTTP 400.
14. IF `PATCH /products/{id}/status` is called with an ID that does not correspond to any existing product, THEN THE Products_Router SHALL return HTTP 404.
15. WHEN `POST /products/upload-image` is called with a file whose MIME type is one of `image/jpeg`, `image/png`, `image/webp`, or `image/gif` and whose size is within 5 MB, THE Products_Router SHALL return HTTP 200 and a JSON object containing an `image_url` field with a non-empty string value.
16. IF `POST /products/upload-image` is called with a file whose MIME type is not one of `image/jpeg`, `image/png`, `image/webp`, or `image/gif`, THEN THE Products_Router SHALL return HTTP 400.
17. IF `POST /products/upload-image` is called with a file whose size exceeds 5 MB (5,242,880 bytes), THEN THE Products_Router SHALL return HTTP 400.

---

### Requirement 8: Payments Router Integration Tests

**User Story:** As a developer, I want integration tests for `app/routers/payments.py`, so that I can verify that payment history queries return correct summaries, respect date filters, and handle pagination.

#### Acceptance Criteria

1. WHEN `GET /payments` is called with a valid Bearer token and no payments exist in the database, THE Payments_Router SHALL return HTTP 200 and a response envelope containing a `payments` list that is empty and summary fields `count`, `total_ventas`, `total_propinas`, and `total_con_propinas` all equal to `0`.
2. WHEN `GET /payments` is called with a valid Bearer token and payments recorded for the current day exist, THE Payments_Router SHALL return HTTP 200 and a response where `count` equals the number of seeded payments and all summary totals are greater than `0`.
3. WHEN `GET /payments` is called with a valid `date` query parameter in `YYYY-MM-DD` format and a valid Bearer token, THE Payments_Router SHALL return HTTP 200 and a response where every payment in the `payments` list has a `date` field matching the requested date.
4. IF `GET /payments` is called with a `date` query parameter that does not match the `YYYY-MM-DD` format, THEN THE Payments_Router SHALL return HTTP 200 and default to the current date, with the response `date` field equal to today's date in `YYYY-MM-DD` format.
5. WHEN `GET /payments` is called with a `limit` query parameter of value `N` and an `offset` of `0`, THE Payments_Router SHALL return HTTP 200 and a `payments` list containing at most `N` items; WHEN called with an `offset` value greater than or equal to the total number of payments, THE Payments_Router SHALL return HTTP 200 and an empty `payments` list.
6. THE response envelope for `GET /payments` SHALL always contain the fields `payments` (array), `count` (integer), `total_ventas` (number), `total_propinas` (number), and `total_con_propinas` (number).

---

### Requirement 9: Inventory Router Integration Tests

**User Story:** As a developer, I want integration tests for `app/routers/inventory.py`, so that I can verify that inventory queries, stock adjustments, and movement history work correctly with filters and pagination.

#### Acceptance Criteria

1. WHEN `GET /inventory` is called with `page=1` and `limit=N` query parameters and a valid Bearer token, THE Inventory_Router SHALL return HTTP 200 and a response containing at most `N` inventory items; WHEN called with a `page` value beyond the last page, THE Inventory_Router SHALL return HTTP 200 and an empty items list.
2. WHEN `GET /inventory` is called with a `category_id` filter and a valid Bearer token, THE Inventory_Router SHALL return HTTP 200 and only include products whose `category_id` matches the filter value.
3. WHEN `GET /inventory` is called with a valid Bearer token, THE Inventory_Router SHALL return HTTP 200 and a response containing a `low_stock_count` integer field equal to the number of products in the `app/` database whose current stock is strictly below their `min_stock` threshold.
4. WHEN `POST /inventory/adjustments` is called with a positive `quantity`, a valid `product_id`, a `reason` string, and a valid Bearer token with the required permission, THE Inventory_Router SHALL return HTTP 200 and a JSON object containing `movement_type` equal to `"IN"` and the `quantity` value used.
5. WHEN `POST /inventory/adjustments` is called with a negative `quantity` whose absolute value does not exceed the product's current stock, THE Inventory_Router SHALL return HTTP 200 and a JSON object containing `movement_type` equal to `"OUT"`.
6. IF `POST /inventory/adjustments` is called with a negative `quantity` whose absolute value exceeds the product's current stock, THEN THE Inventory_Router SHALL return HTTP 400.
7. IF `POST /inventory/adjustments` is called with a `product_id` that does not exist, THEN THE Inventory_Router SHALL return HTTP 404.
8. WHEN `GET /inventory/movements` is called without filters and a valid Bearer token, THE Inventory_Router SHALL return HTTP 200 and a list containing all recorded inventory movements.
9. WHEN `GET /inventory/movements` is called with a `movement_type` filter, THE Inventory_Router SHALL return HTTP 200 and only movements whose `movement_type` matches the filter value.
10. WHEN `GET /inventory/movements` is called with a `product_id` filter, THE Inventory_Router SHALL return HTTP 200 and only movements whose `product_id` matches the filter value.
11. WHEN `GET /inventory/movements` is called with `start_date` and `end_date` filters in `YYYY-MM-DD` format, THE Inventory_Router SHALL return HTTP 200 and only movements whose recorded date falls within the inclusive range `[start_date, end_date]`.
12. WHEN `GET /inventory/movements` is called with `limit` and `page` query parameters, THE Inventory_Router SHALL return HTTP 200 and apply pagination so that the response contains at most `limit` items starting from the correct offset for the given `page`.

---

### Requirement 10: Coverage Threshold Enforcement

**User Story:** As a developer, I want the test suite to enforce the 80% coverage threshold automatically, so that SonarQube quality gates pass and coverage regressions are caught in CI.

#### Acceptance Criteria

1. WHEN pytest is executed with `--cov=app`, THE Coverage_Tool SHALL measure the line coverage of the `app/` package and report the percentage in the terminal output.
2. IF the measured line coverage of the `app/` package is below 80%, THEN pytest executed with `--cov-fail-under=80` SHALL exit with a non-zero status code.
3. WHEN pytest is executed with `--cov-report=xml:coverage.xml`, THE Coverage_Tool SHALL generate a `coverage.xml` file in the project root that conforms to the Cobertura XML schema (the format SonarQube uses for coverage import via `sonar.python.coverage.reportPaths`).
4. WHEN all tests in `tests/unit/` and `tests/integration/` are executed together, THE Test_Suite SHALL achieve a minimum line coverage of 80% across the `app/` package.
5. WHEN only `tests/unit/` is executed, THE Test_Suite SHALL achieve 100% line coverage for `app/core/security.py`, `app/core/fulfillment.py`, and the three pure functions `should_decrement_product_stock`, `should_record_product_inventory_movement`, and `get_product_cupo_by_stock_field` in `app/services/availability.py`.
