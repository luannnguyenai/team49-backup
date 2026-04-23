"""Tests for KG sync router."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.kg.builder import CycleError
import src.kg.router as kg_router
from src.kg.router import get_settings
from src.kg.schemas import SyncReport


@pytest.mark.asyncio
async def test_kg_sync_returns_report_shape() -> None:
    """POST /kg/sync returns a serialized SyncReport for valid admin token."""

    async def fake_run_build_kg(*, db, config, body):
        assert body.phase == 1
        return SyncReport(created=["concept:1"], updated=[], unchanged=[], soft_deleted=[])

    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        admin_token="secret",
        kg_phase=0,
        allow_legacy_kg_routes=True,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(kg_router, "run_build_kg", fake_run_build_kg)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/kg/sync",
                json={"phase": 1},
                headers={"X-Admin-Token": "secret"},
            )
    finally:
        monkeypatch.undo()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "created": ["concept:1"],
        "updated": [],
        "unchanged": [],
        "soft_deleted": [],
    }


@pytest.mark.asyncio
async def test_kg_sync_rejects_bad_admin_token() -> None:
    """POST /kg/sync rejects missing or wrong admin token."""
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        admin_token="secret",
        kg_phase=0,
        allow_legacy_kg_routes=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/kg/sync", headers={"X-Admin-Token": "wrong"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_kg_sync_cycle_error_returns_500() -> None:
    """CycleError from the pipeline maps to HTTP 500."""

    async def fake_run_build_kg(*, db, config, body):
        raise CycleError("cycle: a -> b -> a")

    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        admin_token="secret",
        kg_phase=0,
        allow_legacy_kg_routes=True,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(kg_router, "run_build_kg", fake_run_build_kg)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/kg/sync", headers={"X-Admin-Token": "secret"})
    finally:
        monkeypatch.undo()
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "cycle" in response.json()["detail"]
