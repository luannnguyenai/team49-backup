from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_logout_revokes_current_bearer_token():
    from src.api.app import app
    from src.schemas.auth import TokenPayload

    payload = TokenPayload(
        sub="user-1",
        type="access",
        exp=9999999999,
        jti="logout-jti",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch("src.routers.auth.decode_token", return_value=payload),
            patch("src.routers.auth.revoke_payload", new=AsyncMock()) as mock_revoke,
        ):
            response = await client.post(
                "/api/auth/logout",
                headers={"Authorization": "Bearer token"},
            )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_revoke.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_logout_rejects_invalid_token():
    from src.api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("src.routers.auth.decode_token", side_effect=ValueError("bad token")):
            response = await client.post(
                "/api/auth/logout",
                headers={"Authorization": "Bearer token"},
            )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token."
