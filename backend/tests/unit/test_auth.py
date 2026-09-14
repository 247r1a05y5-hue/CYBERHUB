"""Authentication unit and integration tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "new_corp_admin@test.com",
        "password": "SecurePassword123!",
        "organization_name": "New Corp Defense",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    tokens = reg_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # 2. Login
    login_payload = {
        "email": "new_corp_admin@test.com",
        "password": "SecurePassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_tokens = login_resp.json()
    assert "access_token" in login_tokens

    # 3. Access /me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_tokens['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "new_corp_admin@test.com"
    assert me_data["role"] == "admin"

    # 4. Refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed = refresh_resp.json()
    assert "access_token" in refreshed
    assert refreshed["access_token"] != login_tokens["access_token"]


@pytest.mark.asyncio
async def test_invalid_login_credentials(client: AsyncClient, test_user):
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!",
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
