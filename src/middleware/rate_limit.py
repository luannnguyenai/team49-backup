"""
middleware/rate_limit.py
-------------------------
Redis-backed sliding-window rate limiter.

Replaces the in-process _SlidingWindowRateLimiter which is broken under
multiple uvicorn workers (each worker has its own counter).
###
Algorithm
---------
For each request, atomically:
  1. Drop entries older than (now - window_sec) from the sorted set
  2. Add the current timestamp
  3. Count entries in the window
  4. Reset TTL

If count > limit, the request is blocked.
"""

import time
from typing import Protocol


class RedisLike(Protocol):
    def pipeline(self): ...


async def check_rate_limit(
    redis: RedisLike,
    key: str,
    limit: int,
    window_sec: int,
) -> bool:
    """Return True if the request is allowed, False if over limit."""
    now = time.time()
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_sec)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window_sec)
    results = await pipe.execute()
    count = results[2]
    return count <= limit
