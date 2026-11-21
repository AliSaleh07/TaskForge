"""Tests for authentication, registration, password hashing, and token validation."""

import pytest
from starlette.testclient import TestClient
from taskforge.auth import hash_password, verify_password


def test_password_hashing():
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert hashed.startswith("pbkdf2:sha256:600000$")
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_user_registration_and_login(client: TestClient):
    # 1. Register successfully
    reg_payload = {
        "username": "alice_dev",
        "email": "alice@example.com",
        "password": "ValidPassword123",
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "alice_dev"
    assert data["email"] == "alice@example.com"
    assert "id" in data

    # 2. Duplicate username rejection
    res_dup = client.post("/api/v1/auth/register", json=reg_payload)
    assert res_dup.status_code == 409
    assert "already taken" in res_dup.json()["detail"]

    # 3. Weak password rejection
    res_weak = client.post(
        "/api/v1/auth/register",
        json={"username": "bob_weak", "email": "bob@example.com", "password": "weak"},
    )
    assert res_weak.status_code == 422

    # 4. Login with correct credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "alice_dev", "password": "ValidPassword123"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]

    # 5. Access /me profile endpoint
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "alice_dev"

    # 6. Unauthorized access without token
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # 7. Login with wrong password
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "alice_dev", "password": "WrongPassword999"},
    )
    assert bad_login.status_code == 401
