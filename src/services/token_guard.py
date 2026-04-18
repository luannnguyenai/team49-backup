"""
services/token_guard.py
-----------------------
Helpers for checking and revoking decoded JWT payloads against the Redis denylist.

Graceful fallback:
- If Redis is not initialized, treat tokens as not revoked so local tools/tests
  that do not run the FastAPI lifespan keep working.
"""

from src.redis_client import get_redis
from src.schemas.auth import TokenPayload
from src.services.auth_service import get_token_remaining_seconds
from src.services.token_denylist import is_token_revoked, revoke_token


async def is_payload_revoked(payload: TokenPayload) -> bool:
    try:
        redis = get_redis()
    except RuntimeError:
        return False

    return await is_token_revoked(redis, payload.jti)


async def revoke_payload(payload: TokenPayload) -> None:
    redis = get_redis()
    await revoke_token(redis, payload.jti, get_token_remaining_seconds(payload))
