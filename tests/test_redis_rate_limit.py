"""
tests/test_redis_rate_limit.py
-------------------------------
RED phase: Redis-backed sliding-window rate limiter + token denylist.
Uses mocked Redis — no live Redis required.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_rate_limit_allows_within_limit():
    """count <= limit → allowed (returns True)."""
    from src.middleware.rate_limit import check_rate_limit

    redis = MagicMock()
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[None, None, 3, None])
    redis.pipeline = MagicMock(return_value=pipe)

    allowed = await check_rate_limit(redis, "rl:login:1.2.3.4", limit=5, window_sec=60)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_limit():
    """count > limit → blocked (returns False)."""
    from src.middleware.rate_limit import check_rate_limit

    redis = MagicMock()
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[None, None, 6, None])
    redis.pipeline = MagicMock(return_value=pipe)

    allowed = await check_rate_limit(redis, "rl:login:1.2.3.4", limit=5, window_sec=60)
    assert allowed is False


@pytest.mark.asyncio
async def test_token_revoke_sets_key_with_ttl():
    """revoke_token writes `revoked:<jti>` with TTL."""
    from src.services.token_denylist import revoke_token

    redis = MagicMock()
    redis.setex = AsyncMock(return_value=True)

    await revoke_token(redis, jti="abc123", expires_in=1800)
    redis.setex.assert_awaited_once_with("revoked:abc123", 1800, "1")


@pytest.mark.asyncio
async def test_is_token_revoked_returns_true_when_key_exists():
    from src.services.token_denylist import is_token_revoked

    redis = MagicMock()
    redis.exists = AsyncMock(return_value=1)
    assert await is_token_revoked(redis, "abc123") is True


@pytest.mark.asyncio
async def test_is_token_revoked_returns_false_when_key_missing():
    from src.services.token_denylist import is_token_revoked

    redis = MagicMock()
    redis.exists = AsyncMock(return_value=0)
    assert await is_token_revoked(redis, "abc123") is False
