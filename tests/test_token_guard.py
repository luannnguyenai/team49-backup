from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_is_payload_revoked_returns_false_when_redis_unavailable():
    from src.schemas.auth import TokenPayload
    from src.services.token_guard import is_payload_revoked

    payload = TokenPayload(sub="user-1", type="access", exp=9999999999, jti="jti-1")

    with patch("src.services.token_guard.get_redis", side_effect=RuntimeError("Redis not initialized")):
        assert await is_payload_revoked(payload) is False


@pytest.mark.asyncio
async def test_is_payload_revoked_uses_redis_lookup_when_available():
    from src.schemas.auth import TokenPayload
    from src.services.token_guard import is_payload_revoked

    payload = TokenPayload(sub="user-1", type="access", exp=9999999999, jti="jti-2")
    redis = object()

    with (
        patch("src.services.token_guard.get_redis", return_value=redis),
        patch("src.services.token_guard.is_token_revoked", new=AsyncMock(return_value=True)) as mock_check,
    ):
        assert await is_payload_revoked(payload) is True

    mock_check.assert_awaited_once_with(redis, "jti-2")


@pytest.mark.asyncio
async def test_revoke_payload_uses_remaining_ttl():
    from src.schemas.auth import TokenPayload
    from src.services.token_guard import revoke_payload

    payload = TokenPayload(sub="user-1", type="access", exp=9999999999, jti="jti-3")
    redis = object()

    with (
        patch("src.services.token_guard.get_redis", return_value=redis),
        patch("src.services.token_guard.get_token_remaining_seconds", return_value=1800),
        patch("src.services.token_guard.revoke_token", new=AsyncMock()) as mock_revoke,
    ):
        await revoke_payload(payload)

    mock_revoke.assert_awaited_once_with(redis, "jti-3", 1800)
