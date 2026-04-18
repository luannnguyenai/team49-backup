from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_is_login_allowed_uses_redis_rate_limit_when_available():
    from src.routers.auth import _is_login_allowed

    redis = object()

    with (
        patch("src.routers.auth.get_redis", return_value=redis),
        patch("src.routers.auth.check_rate_limit", new=AsyncMock(return_value=False)) as mock_check,
    ):
        allowed = await _is_login_allowed("1.2.3.4")

    assert allowed is False
    mock_check.assert_awaited_once_with(
        redis,
        "rl:login:1.2.3.4",
        limit=5,
        window_sec=60,
    )


@pytest.mark.asyncio
async def test_is_login_allowed_falls_back_to_in_memory_limiter_when_redis_missing():
    from src.routers.auth import _is_login_allowed

    with (
        patch("src.routers.auth.get_redis", side_effect=RuntimeError("Redis not initialized")),
        patch("src.routers.auth.check_rate_limit", new=AsyncMock()) as mock_check,
        patch("src.routers.auth._login_limiter.is_allowed", return_value=True) as mock_memory,
    ):
        allowed = await _is_login_allowed("5.6.7.8")

    assert allowed is True
    mock_memory.assert_called_once_with("5.6.7.8")
    mock_check.assert_not_awaited()
