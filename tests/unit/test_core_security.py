"""Unit tests for app/core/security.py — no DB or HTTP client imports."""
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# hash_password
# ---------------------------------------------------------------------------

def test_hash_password_returns_non_empty_string():
    result = hash_password("mypassword")
    assert isinstance(result, str) and len(result) > 0


def test_hash_password_differs_from_input():
    pw = "mypassword"
    assert hash_password(pw) != pw


def test_hash_password_is_non_deterministic():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------

def test_verify_password_correct():
    hashed = hash_password("secret")
    assert verify_password("secret", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("secret")
    assert verify_password("wrong", hashed) is False


def test_verify_password_empty_wrong():
    hashed = hash_password("secret")
    assert verify_password("", hashed) is False


# ---------------------------------------------------------------------------
# create_access_token / create_refresh_token / decode_token
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("user_id,role", [
    (1, "admin"),
    (42, "waiter"),
    (99, "cashier"),
])
def test_create_access_token_payload(user_id, role):
    token = create_access_token(user_id, role)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role
    assert payload["type"] == "access"


@pytest.mark.parametrize("user_id,role", [
    (1, "admin"),
    (7, "waiter"),
])
def test_create_refresh_token_payload(user_id, role):
    token = create_refresh_token(user_id, role)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role
    assert payload["type"] == "refresh"


def test_refresh_token_exp_greater_than_access_token():
    access = create_access_token(1, "admin")
    refresh = create_refresh_token(1, "admin")
    access_payload = decode_token(access)
    refresh_payload = decode_token(refresh)
    assert refresh_payload["exp"] > access_payload["exp"]


def test_decode_token_contains_required_claims():
    token = create_access_token(5, "admin")
    payload = decode_token(token)
    for key in ("sub", "role", "type", "jti", "iat", "exp"):
        assert key in payload


def test_decode_token_invalid_returns_none():
    assert decode_token("not.a.valid.token") is None


def test_decode_token_empty_string_returns_none():
    assert decode_token("") is None


def test_decode_token_tampered_returns_none():
    token = create_access_token(1, "admin")
    tampered = token[:-5] + "XXXXX"
    assert decode_token(tampered) is None
