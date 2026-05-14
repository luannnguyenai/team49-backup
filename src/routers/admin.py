"""
routers/admin.py
----------------
Admin dashboard API. All endpoints require role='admin' via require_admin dep.

    GET /api/admin/stats/overview        — KPI rollup
    GET /api/admin/users                 — paginated user list
    GET /api/admin/signups/timeseries    — signups per day
    GET /api/admin/llm/recent            — tail qa_history.jsonl
    GET /api/admin/llm/stats             — LLM usage rollup
    GET /api/admin/system/health         — CPU/RAM/DB/Redis snapshot
    GET /api/admin/traffic/summary       — Prometheus rate snapshot
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import boto3
import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_async_db
from src.dependencies.auth import require_admin
from src.models.user import User
from src.services.model_registry import check_all_chat_model_health

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None  # graceful degradation

def _running_in_ecs() -> bool:
    return bool(
        os.getenv("ECS_CONTAINER_METADATA_URI_V4")
        or os.getenv("ECS_CONTAINER_METADATA_URI")
        or os.getenv("AWS_EXECUTION_ENV", "").startswith("AWS_ECS")
    )


LOG_DIR = Path(os.getenv("AI_LOG_DIR") or "logs")
QA_LOG = LOG_DIR / "qa_history.jsonl"
ACCESS_LOG = LOG_DIR / "access.jsonl"
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus.obs.a20-prod.internal:9090" if _running_in_ecs() else "http://localhost:9090",
)
LOKI_URL = os.getenv(
    "LOKI_URL",
    "http://loki.obs.a20-prod.internal:3100" if _running_in_ecs() else "http://host.docker.internal:3100",
)
APP_BOOT_TS = datetime.now(UTC)
CONTAINER_LOG_ALLOWLIST = (
    "al_backend",
    "al_frontend",
    "al_db",
    "al_redis",
    "a20_promtail",
    "a20_loki",
    "a20_grafana",
    "a20_prometheus",
)
CLOUDWATCH_LOG_GROUPS_ENV = "AWS_CLOUDWATCH_LOG_GROUPS"
DEFAULT_CLOUDWATCH_LOG_GROUPS = (
    "/ecs/a20-backend",
    "/ecs/a20-frontend",
    "/ecs/a20-backend-migrate",
    "/ecs/a20-backend-bootstrap",
    "/ecs/a20-backend-seed-core",
    "/ecs/a20-backend-sync-schema-v2",
    "/ecs/a20-backend-seed-accounts",
)

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    # Read last N lines without loading the whole file
    lines: list[bytes] = []
    with path.open("rb") as f:
        try:
            f.seek(0, 2)
            size = f.tell()
            block = 8192
            data = b""
            while size > 0 and len(lines) <= limit + 50:
                step = min(block, size)
                size -= step
                f.seek(size)
                data = f.read(step) + data
                lines = data.splitlines()
            lines = lines[-limit:]
        except OSError:
            f.seek(0)
            lines = f.readlines()[-limit:]
    out: list[dict[str, Any]] = []
    for raw in lines:
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def _parse_timestamp(value: Any) -> datetime:
    if value is None:
        return datetime.fromtimestamp(0, tz=UTC)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return datetime.fromtimestamp(0, tz=UTC)


def _event_sort_key(event: dict[str, Any]) -> datetime:
    return _parse_timestamp(event.get("timestamp"))


def _build_source_state(status: str, count: int = 0, message: str | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "count": count,
        "message": message,
    }


def _guess_level(raw: dict[str, Any], fallback: str = "info") -> str:
    level = raw.get("level")
    if isinstance(level, str) and level.strip():
        return level.lower()

    status = raw.get("status")
    try:
        status_code = int(status)
    except (TypeError, ValueError):
        status_code = None

    if raw.get("error") or status == "error":
        return "error"
    if status_code is not None and status_code >= 500:
        return "error"
    if status_code is not None and status_code >= 400:
        return "warn"
    return fallback


def _normalize_app_event(raw: dict[str, Any], index: int) -> dict[str, Any]:
    timestamp = raw.get("timestamp") or raw.get("ts") or raw.get("created_at")
    message = (
        raw.get("message")
        or raw.get("question")
        or raw.get("answer")
        or "QA history event"
    )
    return {
        "id": f"app-{index}",
        "timestamp": str(timestamp) if timestamp else None,
        "source": "app",
        "service": "backend",
        "level": _guess_level(raw),
        "message": str(message),
        "request_id": raw.get("request_id"),
        "user_id": raw.get("user_id") or raw.get("user"),
        "trace_id": raw.get("langfuse_trace_id") or raw.get("trace_id"),
        "raw": raw,
    }


def _normalize_access_event(raw: dict[str, Any], index: int) -> dict[str, Any]:
    status = raw.get("status")
    message = f'{raw.get("method", "REQ")} {raw.get("path", "/")} {status or "unknown"}'
    return {
        "id": f"access-{index}",
        "timestamp": raw.get("ts") or raw.get("timestamp") or raw.get("created_at"),
        "source": "access",
        "service": "backend",
        "level": _guess_level(raw),
        "message": message,
        "request_id": raw.get("request_id"),
        "user_id": raw.get("user_id"),
        "trace_id": raw.get("trace_id"),
        "raw": raw,
    }


def _read_app_log_events(limit: int) -> list[dict[str, Any]]:
    return [_normalize_app_event(raw, index) for index, raw in enumerate(_read_jsonl_tail(QA_LOG, limit), start=1)]


def _read_access_log_events(limit: int) -> list[dict[str, Any]]:
    return [
        _normalize_access_event(raw, index)
        for index, raw in enumerate(_read_jsonl_tail(ACCESS_LOG, limit), start=1)
    ]


def _candidate_loki_urls() -> list[str]:
    candidates = [os.getenv("LOKI_URL", LOKI_URL)]
    if not _running_in_ecs():
        candidates.extend(
            [
                "http://host.docker.internal:3100",
                "http://localhost:3100",
            ]
        )
    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _cloudwatch_log_groups() -> list[str]:
    configured = os.getenv(CLOUDWATCH_LOG_GROUPS_ENV, "")
    if configured.strip():
        return [item.strip() for item in configured.split(",") if item.strip()]
    return list(DEFAULT_CLOUDWATCH_LOG_GROUPS)


def _normalize_cloudwatch_event(raw: dict[str, Any], index: int) -> dict[str, Any]:
    message_text = raw.get("message", "")
    raw_payload: dict[str, Any]
    try:
        parsed = json.loads(message_text)
        raw_payload = parsed if isinstance(parsed, dict) else {"message": parsed}
    except Exception:
        raw_payload = {"message": message_text}

    service = str(raw.get("logGroupName") or raw.get("log_group") or "cloudwatch").removeprefix("/ecs/")
    return {
        "id": f"cloudwatch-{index}",
        "timestamp": datetime.fromtimestamp(
            int(raw.get("timestamp", 0)) / 1000,
            tz=UTC,
        ).isoformat()
        if raw.get("timestamp") is not None
        else None,
        "source": "cloudwatch",
        "service": service,
        "level": _guess_level(raw_payload, fallback="info"),
        "message": str(
            raw_payload.get("message")
            or raw_payload.get("question")
            or raw_payload.get("path")
            or message_text
            or "CloudWatch event"
        )[:400],
        "request_id": raw_payload.get("request_id"),
        "user_id": raw_payload.get("user_id") or raw_payload.get("user"),
        "trace_id": raw_payload.get("trace_id"),
        "raw": {
            "logGroup": raw.get("logGroupName"),
            "logStream": raw.get("logStreamName"),
            "payload": raw_payload,
        },
    }


def _get_cloudwatch_source_status() -> dict[str, Any]:
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not region:
        return _build_source_state("unavailable", 0, "AWS region is not configured")
    groups = _cloudwatch_log_groups()
    if not groups:
        return _build_source_state("unavailable", 0, "No CloudWatch log groups configured")
    return _build_source_state("healthy", len(groups), None)


async def _fetch_cloudwatch_events(limit: int) -> list[dict[str, Any]]:
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    groups = _cloudwatch_log_groups()
    if not region or not groups:
        return []

    client = boto3.client("logs", region_name=region)
    start_time = int((datetime.now(UTC) - timedelta(hours=6)).timestamp() * 1000)
    per_group_limit = max(1, min(50, limit))
    events: list[dict[str, Any]] = []

    for group in groups:
        try:
            response = client.filter_log_events(
                logGroupName=group,
                startTime=start_time,
                limit=per_group_limit,
                interleaved=True,
            )
        except Exception:
            continue

        for raw in response.get("events", []):
            enriched = {
                **raw,
                "logGroupName": group,
            }
            events.append(enriched)

    normalized = [
        _normalize_cloudwatch_event(raw, index)
        for index, raw in enumerate(sorted(events, key=lambda event: event.get("timestamp", 0), reverse=True), start=1)
    ]
    return normalized[:limit]


async def _fetch_loki_events(limit: int, query: str | None = None) -> list[dict[str, Any]]:
    logql = query or '{app="a20-app-049"}'
    end = datetime.now(UTC)
    start = end - timedelta(hours=6)

    async with httpx.AsyncClient() as client:
        for base_url in _candidate_loki_urls():
            try:
                response = await client.get(
                    f"{base_url}/loki/api/v1/query_range",
                    params={
                        "query": logql,
                        "start": int(start.timestamp() * 1_000_000_000),
                        "end": int(end.timestamp() * 1_000_000_000),
                        "limit": limit,
                        "direction": "BACKWARD",
                    },
                    timeout=3.0,
                )
                if response.status_code != 200:
                    continue
                result = response.json().get("data", {}).get("result", [])
                events: list[dict[str, Any]] = []
                for stream_index, stream in enumerate(result, start=1):
                    labels = stream.get("stream", {})
                    for line_index, (timestamp_ns, line) in enumerate(stream.get("values", []), start=1):
                        try:
                            timestamp = datetime.fromtimestamp(
                                int(timestamp_ns) / 1_000_000_000,
                                tz=UTC,
                            ).isoformat()
                        except Exception:
                            timestamp = None
                        try:
                            raw = json.loads(line)
                        except Exception:
                            raw = {"line": line}
                        events.append(
                            {
                                "id": f"loki-{stream_index}-{line_index}",
                                "timestamp": timestamp,
                                "source": "loki",
                                "service": labels.get("job", "loki"),
                                "level": _guess_level(raw),
                                "message": str(
                                    raw.get("message")
                                    or raw.get("question")
                                    or raw.get("path")
                                    or raw.get("line")
                                    or "Loki event"
                                ),
                                "request_id": raw.get("request_id"),
                                "user_id": raw.get("user_id") or raw.get("user"),
                                "trace_id": raw.get("trace_id"),
                                "raw": {
                                    "labels": labels,
                                    "payload": raw,
                                },
                            }
                        )
                return events
            except Exception:
                continue
    return []


def _get_runtime_source_status() -> dict[str, Any]:
    if _running_in_ecs():
        return _build_source_state("skipped", 0, "container logs are not available on ECS")
    if shutil.which("docker") is None:
        return _build_source_state("unavailable", 0, "docker cli not available")

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=4,
            check=True,
        )
    except Exception as exc:
        return _build_source_state("unavailable", 0, f"docker runtime unavailable: {exc}")

    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    matched = [name for name in names if name in CONTAINER_LOG_ALLOWLIST]
    return _build_source_state("healthy", len(matched), None)


async def _fetch_container_events(limit: int) -> list[dict[str, Any]]:
    if _running_in_ecs():
        return []
    if shutil.which("docker") is None:
        return []

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=4,
            check=True,
        )
    except Exception:
        return []

    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    matched = [name for name in names if name in CONTAINER_LOG_ALLOWLIST]
    per_container_limit = max(1, min(20, limit // max(1, len(matched))))
    events: list[dict[str, Any]] = []
    for container in matched:
        try:
            logs_result = subprocess.run(
                ["docker", "logs", "--tail", str(per_container_limit), container],
                capture_output=True,
                text=True,
                timeout=4,
                check=True,
            )
        except Exception:
            continue
        lines = [line for line in logs_result.stdout.splitlines() if line.strip()]
        for index, line in enumerate(lines, start=1):
            events.append(
                {
                    "id": f"container-{container}-{index}",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": "container",
                    "service": container,
                    "level": "info",
                    "message": line[:280],
                    "request_id": None,
                    "user_id": None,
                    "trace_id": None,
                    "raw": {"line": line, "container": container},
                }
            )
    return events


async def _collect_logs(
    limit: int,
    sources: list[str] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected_sources = set(sources or ["cloudwatch", "app", "access", "loki", "container"])
    events: list[dict[str, Any]] = []
    states: dict[str, Any] = {}

    cloudwatch_state = _get_cloudwatch_source_status()
    if "cloudwatch" in selected_sources:
        cloudwatch_events = await _fetch_cloudwatch_events(limit)
        events.extend(cloudwatch_events)
        states["cloudwatch"] = {
            **cloudwatch_state,
            "count": len(cloudwatch_events) if cloudwatch_state["status"] == "healthy" else cloudwatch_state["count"],
        }
    else:
        states["cloudwatch"] = _build_source_state("skipped", 0, None)

    if "app" in selected_sources:
        app_events = _read_app_log_events(limit)
        events.extend(app_events)
        states["app"] = _build_source_state("healthy", len(app_events), None)
    else:
        states["app"] = _build_source_state("skipped", 0, None)

    if "access" in selected_sources:
        access_events = _read_access_log_events(limit)
        events.extend(access_events)
        states["access"] = _build_source_state("healthy", len(access_events), None)
    else:
        states["access"] = _build_source_state("skipped", 0, None)

    if "loki" in selected_sources:
        loki_events = await _fetch_loki_events(limit)
        events.extend(loki_events)
        states["loki"] = _build_source_state(
            "healthy" if loki_events else "degraded",
            len(loki_events),
            None if loki_events else "no Loki events returned",
        )
    else:
        states["loki"] = _build_source_state("skipped", 0, None)

    runtime_state = _get_runtime_source_status()
    if "container" in selected_sources:
        container_events = await _fetch_container_events(limit)
        events.extend(container_events)
        states["container"] = (
            {
                **runtime_state,
                "count": len(container_events),
            }
            if runtime_state["status"] == "healthy"
            else runtime_state
        )
    else:
        states["container"] = _build_source_state("skipped", 0, None)

    return sorted(events, key=_event_sort_key, reverse=True), states


async def _prom_query(client: httpx.AsyncClient, query: str) -> float | None:
    try:
        r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=2.0)
        if r.status_code != 200:
            return None
        data = r.json().get("data", {}).get("result", [])
        if not data:
            return None
        return float(data[0]["value"][1])
    except Exception:
        return None


async def _prom_query_range(
    client: httpx.AsyncClient,
    query: str,
    *,
    start: datetime,
    end: datetime,
    step_seconds: int,
) -> list[tuple[datetime, float]]:
    try:
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step_seconds,
            },
            timeout=3.0,
        )
        if r.status_code != 200:
            return []
        result = r.json().get("data", {}).get("result", [])
        if not result:
            return []
        values = result[0].get("values", [])
        series: list[tuple[datetime, float]] = []
        for ts_raw, value_raw in values:
            try:
                point_ts = datetime.fromtimestamp(float(ts_raw), tz=UTC)
                point_value = float(value_raw)
            except Exception:
                continue
            series.append((point_ts, point_value))
        return series
    except Exception:
        return []


def _merge_tutor_latency_series(
    metric_series: dict[str, list[tuple[datetime, float]]],
) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for field, points in metric_series.items():
        for point_ts, value in points:
            bucket = point_ts.replace(minute=0, second=0, microsecond=0).isoformat()
            row = rows.setdefault(bucket, {"hour": bucket})
            row[field] = round(value, 2)

    ordered_rows = [rows[key] for key in sorted(rows.keys())]
    for row in ordered_rows:
        row.setdefault("first_status_p50_ms", None)
        row.setdefault("first_status_p95_ms", None)
        row.setdefault("first_answer_p50_ms", None)
        row.setdefault("first_answer_p95_ms", None)
        row.setdefault("sample_count", None)
    return ordered_rows


async def _load_tutor_latency_timeseries(
    client: httpx.AsyncClient,
    *,
    hours: int,
) -> list[dict[str, Any]]:
    end = datetime.now(UTC)
    start = end - timedelta(hours=hours)
    step_seconds = 3600

    metric_queries = {
        "first_status_p50_ms": (
            "1000 * histogram_quantile(0.50, "
            "sum by (le) (rate(tutor_stream_first_status_seconds_bucket[1h])))"
        ),
        "first_status_p95_ms": (
            "1000 * histogram_quantile(0.95, "
            "sum by (le) (rate(tutor_stream_first_status_seconds_bucket[1h])))"
        ),
        "first_answer_p50_ms": (
            "1000 * histogram_quantile(0.50, "
            "sum by (le) (rate(tutor_stream_first_answer_seconds_bucket[1h])))"
        ),
        "first_answer_p95_ms": (
            "1000 * histogram_quantile(0.95, "
            "sum by (le) (rate(tutor_stream_first_answer_seconds_bucket[1h])))"
        ),
        "sample_count": ("sum(increase(tutor_stream_total_seconds_count[1h]))"),
    }

    metric_series: dict[str, list[tuple[datetime, float]]] = {}
    for field, query in metric_queries.items():
        metric_series[field] = await _prom_query_range(
            client,
            query,
            start=start,
            end=end,
            step_seconds=step_seconds,
        )

    return _merge_tutor_latency_series(metric_series)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
@admin_router.get("/stats/overview")
async def stats_overview(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    signups_7d = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= week_ago))
    ).scalar_one()

    # DAU/MAU best-effort via sessions table; fallback to access log for active users.
    dau = mau = active_now = 0
    fifteen_min_ago = now - timedelta(minutes=15)
    one_hour_ago = now - timedelta(hours=1)
    try:
        dau = (
            await db.execute(
                text("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE started_at >= :since"),
                {"since": day_ago},
            )
        ).scalar_one() or 0
        mau = (
            await db.execute(
                text("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE started_at >= :since"),
                {"since": month_ago},
            )
        ).scalar_one() or 0
        active_now = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM sessions
                    WHERE started_at >= :recent
                       OR (completed_at IS NULL AND started_at >= :open_since)
                    """
                ),
                {"recent": fifteen_min_ago, "open_since": one_hour_ago},
            )
        ).scalar_one() or 0
    except Exception:
        pass

    # LLM rollup from qa_history table
    llm_calls_24h = 0
    try:
        llm_calls_24h = (
            await db.execute(
                text("SELECT COUNT(*) FROM qa_history WHERE created_at >= :since"),
                {"since": day_ago.replace(tzinfo=None)},
            )
        ).scalar_one() or 0
    except Exception:
        pass

    # Traffic / latency from Prometheus (best-effort)
    avg_latency_ms = None
    error_rate = None
    async with httpx.AsyncClient() as client:
        p95 = await _prom_query(
            client,
            'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="fastapi"}[5m])))',
        )
        if p95 is not None:
            avg_latency_ms = round(p95 * 1000, 2)
        err = await _prom_query(
            client,
            'sum(rate(http_requests_total{job="fastapi",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="fastapi"}[5m])),1e-9)',
        )
        if err is not None:
            error_rate = round(err, 6)

    uptime_seconds = (now - APP_BOOT_TS).total_seconds()

    return {
        "total_users": int(total_users),
        "dau": int(dau),
        "mau": int(mau),
        "active_now": int(active_now),
        "signups_7d": int(signups_7d),
        "llm_calls_24h": int(llm_calls_24h),
        "avg_latency_ms": avg_latency_ms,
        "error_rate": error_rate,
        "uptime_seconds": int(uptime_seconds),
    }


@admin_router.get("/model/current")
async def current_model(_admin: User = Depends(require_admin)) -> dict[str, Any]:
    return {
        "name": settings.default_model,
        "provider": settings.model_provider,
        "fast_model": settings.fast_model,
    }


@admin_router.get("/model/health")
async def model_health(_admin: User = Depends(require_admin)) -> dict[str, Any]:
    return {"models": await check_all_chat_model_health()}


@admin_router.get("/users")
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: str | None = Query(None, description="Search by email or full_name (ILIKE)"),
) -> dict[str, Any]:
    stmt = select(User).order_by(User.created_at.desc())
    count_stmt = select(func.count(User.id))
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
        count_stmt = count_stmt.where((User.email.ilike(like)) | (User.full_name.ilike(like)))
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "total": int(total),
        "page": page,
        "size": size,
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_onboarded": u.is_onboarded,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ],
    }


@admin_router.get("/signups/timeseries")
async def signups_timeseries(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
    days: int = Query(30, ge=1, le=365),
) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        await db.execute(
            text(
                """
                SELECT date_trunc('day', created_at)::date AS day, COUNT(*)::int AS c
                FROM users
                WHERE created_at >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since},
        )
    ).all()
    return [{"date": r[0].isoformat(), "count": int(r[1])} for r in rows]


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
@admin_router.get("/llm/recent")
async def llm_recent(
    _admin: User = Depends(require_admin),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict[str, Any]]:
    return _read_jsonl_tail(QA_LOG, limit)


@admin_router.get("/llm/stats")
async def llm_stats(
    _admin: User = Depends(require_admin),
    hours: int = Query(24, ge=1, le=24 * 30),
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    entries = _read_jsonl_tail(QA_LOG, limit=5000)

    calls_per_hour: Counter[str] = Counter()
    user_calls: Counter[str] = Counter()
    errors = 0
    total = 0
    for e in entries:
        ts_raw = e.get("timestamp") or e.get("ts") or e.get("created_at")
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")) if ts_raw else None
        except Exception:
            ts = None
        if ts is None or ts < cutoff:
            continue
        total += 1
        bucket = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        calls_per_hour[bucket] += 1
        uid = e.get("user_id") or e.get("user") or "anonymous"
        user_calls[str(uid)] += 1
        if e.get("error") or e.get("status") == "error":
            errors += 1

    async with httpx.AsyncClient() as client:
        tutor_latency_per_hour = await _load_tutor_latency_timeseries(
            client,
            hours=hours,
        )

    return {
        "window_hours": hours,
        "total_calls": total,
        "errors": errors,
        "calls_per_hour": [{"hour": h, "count": c} for h, c in sorted(calls_per_hour.items())],
        "top_users": [{"user_id": u, "count": c} for u, c in user_calls.most_common(5)],
        "tutor_latency_per_hour": tutor_latency_per_hour,
    }


# ---------------------------------------------------------------------------
# Logs explorer
# ---------------------------------------------------------------------------
@admin_router.get("/logs/events")
async def logs_events(
    _admin: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
    sources: list[str] | None = Query(None),
) -> dict[str, Any]:
    events, states = await _collect_logs(limit, sources)
    return {
        "total": len(events),
        "items": events[:limit],
        "sources": states,
    }


@admin_router.get("/logs/summary")
async def logs_summary(
    _admin: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    events, states = await _collect_logs(limit, ["cloudwatch", "app", "access", "loki", "container"])
    services = {event["service"] for event in events if event.get("service")}
    totals = {
        "events": len(events),
        "errors": sum(1 for event in events if event.get("level") == "error"),
        "warnings": sum(1 for event in events if event.get("level") == "warn"),
        "services": len(services),
    }
    return {
        "totals": totals,
        "sources": states,
    }


# ---------------------------------------------------------------------------
# Feedback (Phase 16) — aggregations over qa_history.rating
# ---------------------------------------------------------------------------
@admin_router.get("/feedback/stats")
async def feedback_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
    days: int = Query(14, ge=1, le=180),
) -> dict[str, Any]:
    since_naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    rollup = (
        await db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE rating = 1)::int  AS positive,
                    COUNT(*) FILTER (WHERE rating = -1)::int AS negative,
                    COUNT(*) FILTER (WHERE rating IS NOT NULL)::int AS total
                FROM qa_history
                WHERE created_at >= :since
                """
            ),
            {"since": since_naive},
        )
    ).one()
    positive, negative, total = int(rollup[0]), int(rollup[1]), int(rollup[2])

    unrated_24h = (
        await db.execute(
            text(
                """
                SELECT COUNT(*)::int FROM qa_history
                WHERE rating IS NULL AND created_at >= :since
                """
            ),
            {"since": since_naive + timedelta(days=days - 1)},
        )
    ).scalar_one() or 0

    trend_rows = (
        await db.execute(
            text(
                """
                SELECT
                    date_trunc('day', created_at)::date AS day,
                    COUNT(*) FILTER (WHERE rating = 1)::int  AS positive,
                    COUNT(*) FILTER (WHERE rating = -1)::int AS negative
                FROM qa_history
                WHERE created_at >= :since AND rating IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"since": since_naive},
        )
    ).all()

    return {
        "total_ratings": total,
        "positive": positive,
        "negative": negative,
        "positive_ratio": (positive / total) if total > 0 else None,
        "unrated_24h": int(unrated_24h),
        "trend": [
            {"date": r[0].isoformat(), "positive": int(r[1]), "negative": int(r[2])}
            for r in trend_rows
        ],
    }


@admin_router.get("/feedback/recent-negative")
async def feedback_recent_negative(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            text(
                """
                SELECT id, lecture_id, question, answer, context_binding_id, created_at
                FROM qa_history
                WHERE rating = -1
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        )
    ).all()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": int(r[0]),
                "lecture_id": r[1],
                "question": (r[2] or "")[:500],
                "answer": (r[3] or "")[:500],
                "context_binding_id": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# System / traffic
# ---------------------------------------------------------------------------
@admin_router.get("/system/health")
async def system_health(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    cpu_pct = ram_pct = disk_pct = None
    if psutil is not None:
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            ram_pct = psutil.virtual_memory().percent
            disk_pct = psutil.disk_usage("/").percent
        except Exception:
            pass

    db_status = "down"
    db_connections = 0
    try:
        result = await db.execute(text("SELECT count(*) FROM pg_stat_activity"))
        db_connections = int(result.scalar_one())
        db_status = "healthy"
    except Exception:
        db_status = "down"

    redis_status = "unknown"
    redis_hit_rate = None
    try:
        from src.redis_client import get_redis

        r = get_redis()
        if r is not None:
            info = await r.info("stats")
            hits = int(info.get("keyspace_hits", 0))
            misses = int(info.get("keyspace_misses", 0))
            redis_status = "healthy"
            if hits + misses > 0:
                redis_hit_rate = round(hits / (hits + misses), 4)
        else:
            redis_status = "down"
    except Exception:
        redis_status = "down"

    return {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "disk_pct": disk_pct,
        "db_connections": db_connections,
        "redis_hit_rate": redis_hit_rate,
        "uptime_seconds": int((datetime.now(UTC) - APP_BOOT_TS).total_seconds()),
        "services": [
            {"name": "fastapi", "status": "healthy"},
            {"name": "postgres", "status": db_status},
            {"name": "redis", "status": redis_status},
        ],
    }


@admin_router.get("/traffic/summary")
async def traffic_summary(
    _admin: User = Depends(require_admin),
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        rps = await _prom_query(client, 'sum(rate(http_requests_total{job="fastapi"}[1m]))')
        p50 = await _prom_query(
            client,
            'histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket{job="fastapi"}[5m])))',
        )
        p95 = await _prom_query(
            client,
            'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="fastapi"}[5m])))',
        )
        p99 = await _prom_query(
            client,
            'histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{job="fastapi"}[5m])))',
        )
        err4 = await _prom_query(
            client,
            'sum(rate(http_requests_total{job="fastapi",status=~"4.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="fastapi"}[5m])),1e-9)',
        )
        err5 = await _prom_query(
            client,
            'sum(rate(http_requests_total{job="fastapi",status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total{job="fastapi"}[5m])),1e-9)',
        )
    return {
        "rps_1m": rps,
        "latency_seconds": {"p50": p50, "p95": p95, "p99": p99},
        "rate_4xx": err4,
        "rate_5xx": err5,
        "prometheus_url": PROMETHEUS_URL,
    }
