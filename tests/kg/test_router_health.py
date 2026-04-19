"""Tests for KG health router."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.kg.router import get_kg_health


@pytest.mark.asyncio
async def test_kg_health_returns_counts() -> None:
    """GET /kg/health returns KG count payload."""

    async def fake_get_kg_health():
        return {
            "node_counts_by_kind": {"concept": 2},
            "edge_counts_by_type": {"INSTANCE_OF": 3},
            "last_sync_at": "2026-04-19T00:00:00Z",
        }

    app.dependency_overrides[get_kg_health] = fake_get_kg_health
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/kg/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "node_counts_by_kind": {"concept": 2},
        "edge_counts_by_type": {"INSTANCE_OF": 3},
        "last_sync_at": "2026-04-19T00:00:00Z",
    }
