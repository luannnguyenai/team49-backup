from unittest.mock import AsyncMock, patch

import pytest

from src.routers.admin import llm_stats


@pytest.mark.asyncio
async def test_llm_stats_includes_tutor_latency_timeseries():
    fake_entries = [
        {
            "timestamp": "2026-05-03T00:00:00+00:00",
            "user_id": "user-1",
        },
        {
            "timestamp": "2026-05-03T00:10:00+00:00",
            "user_id": "user-2",
            "status": "error",
        },
    ]
    fake_latency = [
        {
            "hour": "2026-05-03T00:00:00+00:00",
            "first_status_p50_ms": 120.0,
            "first_status_p95_ms": 450.0,
            "first_answer_p50_ms": 380.0,
            "first_answer_p95_ms": 910.0,
            "sample_count": 7.0,
        }
    ]

    with (
        patch("src.routers.admin._read_jsonl_tail", return_value=fake_entries),
        patch(
            "src.routers.admin._load_tutor_latency_timeseries",
            new=AsyncMock(return_value=fake_latency),
        ),
    ):
        result = await llm_stats(_admin=object(), hours=24)

    assert result["window_hours"] == 24
    assert result["total_calls"] == 2
    assert result["errors"] == 1
    assert result["top_users"] == [
        {"user_id": "user-1", "count": 1},
        {"user_id": "user-2", "count": 1},
    ]
    assert result["tutor_latency_per_hour"] == fake_latency
