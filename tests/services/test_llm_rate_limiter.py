from __future__ import annotations

from src.services.llm_rate_limiter import SlidingWindowRateLimiter


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_sliding_window_rate_limiter_sleeps_when_limit_is_reached() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(
        max_requests=2,
        window_seconds=60.0,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )

    limiter.acquire("gemini")
    limiter.acquire("gemini")
    limiter.acquire("gemini")

    assert clock.sleeps == [60.0]


def test_sliding_window_rate_limiter_tracks_buckets_independently() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowRateLimiter(
        max_requests=1,
        window_seconds=60.0,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )

    limiter.acquire("gemini-router")
    limiter.acquire("openai")

    assert clock.sleeps == []
