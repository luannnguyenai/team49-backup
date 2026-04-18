"""
services/token_denylist.py
---------------------------
Redis-backed JWT token denylist for logout/revoke.

Keys are `revoked:<jti>` with TTL = remaining token lifetime, so Redis
reclaims them automatically once the underlying token would expire anyway.
"""


async def revoke_token(redis, jti: str, expires_in: int) -> None:
    """Mark the token's jti as revoked for `expires_in` seconds."""
    await redis.setex(f"revoked:{jti}", expires_in, "1")


async def is_token_revoked(redis, jti: str) -> bool:
    """Return True if the jti is in the denylist."""
    return (await redis.exists(f"revoked:{jti}")) == 1
