from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from src.config import settings


class SlidingWindowRateLimiter:
    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def acquire(self, bucket: str) -> None:
        while True:
            with self._lock:
                timestamps = self._buckets[bucket]
                now = self._clock()
                while timestamps and now - timestamps[0] >= self._window_seconds:
                    timestamps.popleft()

                if len(timestamps) < self._max_requests:
                    timestamps.append(now)
                    return

                wait_seconds = max(0.0, self._window_seconds - (now - timestamps[0]))

            if wait_seconds > 0:
                self._sleep(wait_seconds)


_gemini_rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.gemini_requests_per_minute,
)


def enforce_llm_rate_limit(*, model: str, model_provider: str) -> None:
    provider = model_provider.lower()
    if provider not in {"google_genai", "google", "gemini"}:
        return
    if not model.lower().startswith("gemini"):
        return

    _gemini_rate_limiter.acquire(f"{provider}:{model}")
