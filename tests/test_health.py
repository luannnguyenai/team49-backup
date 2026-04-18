"""
tests/test_health.py
--------------------
Basic smoke tests — validates FastAPI app boots and health endpoint works.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_returns_backend_api_landing(client: AsyncClient):
    """GET / should explain that port 8000 is the backend API surface."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["surface"] == "backend_api"
    assert data["frontend_dev_url"] == "http://127.0.0.1:3000"
    assert data["legacy_static_ui"] == "/static/index.html"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health should return 200 and status=ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_openapi_schema(client: AsyncClient):
    """GET /openapi.json should return a valid schema."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client: AsyncClient):
    """Unauthenticated request to protected endpoint should return 401 or 403."""
    response = await client.get("/api/history")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_register_and_login(db_client: AsyncClient):
    """Register a new user, login, and verify token is returned."""
    # Register
    reg = await db_client.post("/api/auth/register", json={
        "email": "testuser@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
    })
    assert reg.status_code == 201, reg.text
    tokens = reg.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Login
    login = await db_client.post("/api/auth/login", json={
        "email": "testuser@example.com",
        "password": "SecurePass123!",
    })
    assert login.status_code == 200, login.text
    login_tokens = login.json()
    assert "access_token" in login_tokens

    # /api/users/me with token
    me = await db_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {login_tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "testuser@example.com"
