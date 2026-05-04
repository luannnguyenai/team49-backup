from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.routers.admin import current_model, llm_stats


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


@pytest.mark.asyncio
async def test_current_model_returns_settings_values():
    with patch("src.routers.admin.settings") as fake_settings:
        fake_settings.default_model = "claude-sonnet-4-6"
        fake_settings.model_provider = "anthropic"
        fake_settings.fast_model = "claude-haiku-4-5"
        result = await current_model(_admin=object())
    assert result == {
        "name": "claude-sonnet-4-6",
        "provider": "anthropic",
        "fast_model": "claude-haiku-4-5",
    }


@pytest.mark.asyncio
async def test_stats_overview_includes_active_now():
    from src.routers.admin import stats_overview

    # Mock DB so each execute returns a result with .scalar_one() = 0
    async def _exec(*args, **kwargs):
        m = MagicMock()
        m.scalar_one.return_value = 0
        return m

    fake_db = MagicMock()
    fake_db.execute = AsyncMock(side_effect=_exec)

    with patch("src.routers.admin.httpx.AsyncClient") as fake_client:
        fake_client.return_value.__aenter__.return_value = AsyncMock()
        with patch("src.routers.admin._prom_query", new=AsyncMock(return_value=None)):
            result = await stats_overview(_admin=object(), db=fake_db)

    assert "active_now" in result
    assert isinstance(result["active_now"], int)
    assert result["active_now"] == 0
