"""
redis_client.py
----------------
Async Redis client lifecycle + FastAPI dependency.

Created in app lifespan, disposed on shutdown.
Used by:
  - middleware/rate_limit.py  (sliding-window login throttling)
  - services/token_denylist.py (logout/revoke JWT)
"""

from typing import Optional

import redis.asyncio as aioredis

from src.config import settings

_redis: Optional[aioredis.Redis] = None


async def connect_redis() -> aioredis.Redis:
    """Create the global Redis connection. Call from app lifespan."""
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def disconnect_redis() -> None:
    """Close the global Redis connection. Call from app lifespan."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns the shared client."""
    if _redis is None:
        raise RuntimeError("Redis not initialized. Did the app lifespan run?")
    return _redis
