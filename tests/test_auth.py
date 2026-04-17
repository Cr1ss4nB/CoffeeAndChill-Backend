from fastapi.testclient import TestClient


def test_register_success(client: TestClient, session):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "New User",
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "phone": "+1234567890",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New User"
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "client"
    assert "id" in data


def test_register_duplicate_email(client: TestClient, test_data):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Customer Test",
            "email": "customer@example.com",
            "password": "AnotherPassword123!",
        },
    )
    assert response.status_code == 409
    assert "Ya existe" in response.json()["detail"]


def test_login_success_client(client: TestClient, test_data):
    response = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "customerpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["role"] == "client"
    assert data["user"]["email"] == "customer@example.com"


def test_login_success_admin(client: TestClient, test_data):
    response = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "adminpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "admin@example.com"


def test_login_invalid_credentials(client: TestClient, test_data):
    response = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "anypassword"}
    )
    assert response.status_code == 401


def test_get_me_success(client: TestClient, test_data):
    # First, login to get a token
    login_resp = client.post(
        "/auth/login", json={"email": "customer@example.com", "password": "customerpass"}
    )
    token = login_resp.json()["access_token"]

    # Now call /auth/me
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "customer@example.com"
    assert data["role"] == "client"


def test_logout_success(client: TestClient, test_data):
    # First, login
    login_resp = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "adminpass"}
    )
    token = login_resp.json()["access_token"]

    # Call logout
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Sesión cerrada exitosamente"

    # Call /auth/me to verify token is now blacklisted
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 401
    assert "Token revocado" in me_resp.json()["detail"]
