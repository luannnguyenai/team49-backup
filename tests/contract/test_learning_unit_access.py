from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.services.asset_signing import build_signed_asset_url


@pytest.fixture
def protected_video_asset(tmp_path, monkeypatch) -> str:
    asset_path = "courses/CS231n/videos/test-lecture.mp4"
    asset_file = tmp_path / asset_path
    asset_file.parent.mkdir(parents=True)
    asset_file.write_bytes(b"fake-video")
    monkeypatch.setattr("src.api.app.DATA_ROOT", tmp_path)
    return asset_path


@pytest.mark.asyncio
async def test_learning_unit_endpoint_requires_authentication(client):
    response = await client.get("/api/courses/cs231n/units/lecture-1-introduction")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_video_asset_rejects_cookie_auth_fallback_without_signature(client, protected_video_asset):
    with patch(
        "src.api.app.get_current_user_from_request",
        new=AsyncMock(return_value=SimpleNamespace(id="user-1")),
        create=True,
    ):
        response = await client.get(f"/data/{protected_video_asset}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_signed_video_asset_url_loads_without_cookie_auth(client, protected_video_asset):
    now = 1_700_000_000
    signed_url = build_signed_asset_url(
        protected_video_asset,
        expires_in_seconds=300,
        now=now,
    )

    with patch("src.services.asset_signing.time.time", return_value=now):
        response = await client.get(signed_url)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_expired_signed_video_asset_url_is_rejected(client, protected_video_asset):
    now = 1_700_000_000
    signed_url = build_signed_asset_url(
        protected_video_asset,
        expires_in_seconds=60,
        now=now,
    )

    with patch("src.services.asset_signing.time.time", return_value=now + 61):
        response = await client.get(signed_url)

    assert response.status_code == 401
