import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.services.asset_signing import build_signed_asset_url


def _first_cs231n_video_asset_path() -> str:
    units = json.loads(Path("data/course_bootstrap/units.json").read_text(encoding="utf-8"))
    unit = next(unit for unit in units if unit["course_slug"] == "cs231n" and unit.get("video_filename"))
    return f"CS231n/videos/{unit['video_filename']}"


@pytest.mark.asyncio
async def test_learning_unit_endpoint_requires_authentication(client):
    response = await client.get("/api/courses/cs231n/units/lecture-1-introduction")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_video_asset_rejects_cookie_auth_fallback_without_signature(client):
    with patch(
        "src.api.app.get_current_user_from_request",
        new=AsyncMock(return_value=SimpleNamespace(id="user-1")),
        create=True,
    ):
        response = await client.get(f"/data/{_first_cs231n_video_asset_path()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_video_asset_url_loads_without_cookie_auth(client):
    now = 1_700_000_000
    signed_url = build_signed_asset_url(
        _first_cs231n_video_asset_path(),
        expires_in_seconds=300,
        now=now,
    )

    with patch("src.services.asset_signing.time.time", return_value=now):
        response = await client.get(signed_url)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_expired_signed_video_asset_url_is_rejected(client):
    now = 1_700_000_000
    signed_url = build_signed_asset_url(
        _first_cs231n_video_asset_path(),
        expires_in_seconds=60,
        now=now,
    )

    with patch("src.services.asset_signing.time.time", return_value=now + 61):
        response = await client.get(signed_url)

    assert response.status_code == 401
