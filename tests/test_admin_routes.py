from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.routers.admin import (
    _candidate_loki_urls,
    _get_runtime_source_status,
    current_model,
    llm_stats,
    logs_events,
    logs_summary,
    model_health,
)


@pytest.mark.asyncio
async def test_llm_stats_includes_tutor_latency_timeseries():
    now = datetime.now(timezone.utc)
    fake_entries = [
        {
            "timestamp": (now - timedelta(minutes=20)).isoformat(),
            "user_id": "user-1",
        },
        {
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
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
async def test_model_health_returns_registered_models():
    fake_health = [
        {
            "id": "default",
            "label": "Default",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "status": "healthy",
            "latency_ms": 120,
            "checked_at": "2026-05-11T00:00:00+00:00",
            "error": None,
        },
        {
            "id": "qwen35_4b",
            "label": "Qwen 3.5 4B",
            "provider": "openai",
            "model": "qwen3.5-4b-lora",
            "base_url": "https://vllm.a20-app-049.io.vn/v1",
            "status": "healthy",
            "latency_ms": 80,
            "checked_at": "2026-05-11T00:00:00+00:00",
            "error": None,
        },
    ]

    with patch("src.routers.admin.check_all_chat_model_health", new=AsyncMock(return_value=fake_health)):
        result = await model_health(_admin=object())

    assert [item["id"] for item in result["models"]] == ["default", "qwen35_4b"]
    assert result["models"][1]["base_url"] == "https://vllm.a20-app-049.io.vn/v1"


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


@pytest.mark.asyncio
async def test_system_health_reports_redis_healthy_when_client_is_initialized():
    from src.routers.admin import system_health

    db_result = MagicMock()
    db_result.scalar_one.return_value = 3
    fake_db = MagicMock()
    fake_db.execute = AsyncMock(return_value=db_result)

    fake_redis = AsyncMock()
    fake_redis.info.return_value = {
        "keyspace_hits": 9,
        "keyspace_misses": 1,
    }

    with (
        patch("src.routers.admin.psutil", None),
        patch("src.redis_client.get_redis", return_value=fake_redis),
    ):
        result = await system_health(_admin=object(), db=fake_db)

    assert result["db_connections"] == 3
    assert result["redis_hit_rate"] == 0.9
    assert {"name": "postgres", "status": "healthy"} in result["services"]
    assert {"name": "redis", "status": "healthy"} in result["services"]


@pytest.mark.asyncio
async def test_logs_events_merges_selected_sources_and_sorts_descending():
    app_events = [
        {
            "id": "app-1",
            "timestamp": "2026-05-14T08:00:00+00:00",
            "source": "app",
            "service": "backend",
            "level": "info",
            "message": "answer generated",
            "raw": {"question": "What is backprop?"},
        }
    ]
    access_events = [
        {
            "id": "access-1",
            "timestamp": "2026-05-14T08:10:00+00:00",
            "source": "access",
            "service": "backend",
            "level": "error",
            "message": "GET /api/admin/logs 500",
            "raw": {"path": "/api/admin/logs", "status": 500},
        }
    ]
    loki_events = [
        {
            "id": "loki-1",
            "timestamp": "2026-05-14T08:05:00+00:00",
            "source": "loki",
            "service": "loki",
            "level": "warn",
            "message": "promtail delayed",
            "raw": {"stream": {"source": "access"}},
        }
    ]

    with (
        patch("src.routers.admin._read_app_log_events", return_value=app_events),
        patch("src.routers.admin._read_access_log_events", return_value=access_events),
        patch("src.routers.admin._fetch_cloudwatch_events", new=AsyncMock(return_value=[])),
        patch("src.routers.admin._fetch_loki_events", new=AsyncMock(return_value=loki_events)),
        patch("src.routers.admin._fetch_container_events", new=AsyncMock(return_value=[])),
    ):
        result = await logs_events(
            _admin=object(),
            limit=10,
            sources=["app", "access", "loki"],
        )

    assert [event["id"] for event in result["items"]] == ["access-1", "loki-1", "app-1"]
    assert result["total"] == 3
    assert result["sources"]["cloudwatch"]["status"] == "skipped"
    assert result["sources"]["container"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_logs_summary_reports_unavailable_runtime_source_without_failing():
    container_events = []
    container_status = {"status": "unavailable", "message": "docker cli not available"}

    with (
        patch("src.routers.admin._read_app_log_events", return_value=[]),
        patch("src.routers.admin._read_access_log_events", return_value=[]),
        patch("src.routers.admin._fetch_cloudwatch_events", new=AsyncMock(return_value=[])),
        patch("src.routers.admin._fetch_loki_events", new=AsyncMock(return_value=[])),
        patch(
            "src.routers.admin._fetch_container_events",
            new=AsyncMock(return_value=container_events),
        ),
        patch(
            "src.routers.admin._get_runtime_source_status",
            return_value=container_status,
        ),
    ):
        result = await logs_summary(_admin=object(), limit=50)

    assert result["totals"]["events"] == 0
    assert result["sources"]["container"] == container_status


@pytest.mark.asyncio
async def test_logs_summary_prefers_cloudwatch_when_available():
    cloudwatch_events = [
        {
            "id": "cw-1",
            "timestamp": "2026-05-14T08:15:00+00:00",
            "source": "cloudwatch",
            "service": "a20-backend",
            "level": "error",
            "message": "backend crashed",
            "raw": {"logGroup": "/ecs/a20-backend"},
        }
    ]

    with (
        patch("src.routers.admin._read_app_log_events", return_value=[]),
        patch("src.routers.admin._read_access_log_events", return_value=[]),
        patch("src.routers.admin._fetch_cloudwatch_events", new=AsyncMock(return_value=cloudwatch_events)),
        patch("src.routers.admin._get_cloudwatch_source_status", return_value={"status": "healthy", "count": 1, "message": None}),
        patch("src.routers.admin._fetch_loki_events", new=AsyncMock(return_value=[])),
        patch("src.routers.admin._fetch_container_events", new=AsyncMock(return_value=[])),
    ):
        result = await logs_summary(_admin=object(), limit=50)

    assert result["totals"]["events"] == 1
    assert result["totals"]["errors"] == 1
    assert result["sources"]["cloudwatch"]["status"] == "healthy"


def test_candidate_loki_urls_skip_local_fallbacks_on_ecs(monkeypatch):
    monkeypatch.setenv("ECS_CONTAINER_METADATA_URI_V4", "http://169.254.170.2/v4")
    monkeypatch.setenv("LOKI_URL", "http://loki.obs.a20-prod.internal:3100")

    urls = _candidate_loki_urls()

    assert urls == ["http://loki.obs.a20-prod.internal:3100"]


def test_runtime_source_status_skips_container_logs_on_ecs(monkeypatch):
    monkeypatch.setenv("ECS_CONTAINER_METADATA_URI_V4", "http://169.254.170.2/v4")

    status = _get_runtime_source_status()

    assert status["status"] == "skipped"
    assert "ECS" in status["message"]
