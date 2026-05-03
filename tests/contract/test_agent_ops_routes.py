from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.config import settings
from src.database import get_async_db

pytestmark = pytest.mark.anyio


async def _client():
    async def override_db():
        yield SimpleNamespace(commit=AsyncMock())

    app.dependency_overrides[get_async_db] = override_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_pending_action_janitor_requires_admin_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    client = await _client()
    try:
        response = await client.post("/api/agent/ops/pending-actions/janitor")
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_admin_token"


async def test_pending_action_janitor_returns_expired_count(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    with patch(
        "src.routers.agent_ops.AgentPendingActionJanitor.run_once",
        new=AsyncMock(return_value=3),
    ):
        client = await _client()
        try:
            response = await client.post(
                "/api/agent/ops/pending-actions/janitor",
                headers={"x-admin-token": "secret"},
            )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"expired_actions": 3}
