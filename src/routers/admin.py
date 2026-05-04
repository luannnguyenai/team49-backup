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
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_async_db
from src.dependencies.auth import require_admin
from src.models.user import User

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None  # graceful degradation

LOG_DIR = Path("logs")
QA_LOG = LOG_DIR / "qa_history.jsonl"
ACCESS_LOG = LOG_DIR / "access.jsonl"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
APP_BOOT_TS = datetime.now(timezone.utc)

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
                point_ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
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
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    step_seconds = 3600

    metric_queries = {
        "first_status_p50_ms": (
            '1000 * histogram_quantile(0.50, '
            'sum by (le) (rate(tutor_stream_first_status_seconds_bucket[1h])))'
        ),
        "first_status_p95_ms": (
            '1000 * histogram_quantile(0.95, '
            'sum by (le) (rate(tutor_stream_first_status_seconds_bucket[1h])))'
        ),
        "first_answer_p50_ms": (
            '1000 * histogram_quantile(0.50, '
            'sum by (le) (rate(tutor_stream_first_answer_seconds_bucket[1h])))'
        ),
        "first_answer_p95_ms": (
            '1000 * histogram_quantile(0.95, '
            'sum by (le) (rate(tutor_stream_first_answer_seconds_bucket[1h])))'
        ),
        "sample_count": (
            'sum(increase(tutor_stream_total_seconds_count[1h]))'
        ),
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
    now = datetime.now(timezone.utc)
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
                text(
                    "SELECT COUNT(DISTINCT user_id) FROM sessions WHERE started_at >= :since"
                ),
                {"since": day_ago},
            )
        ).scalar_one() or 0
        mau = (
            await db.execute(
                text(
                    "SELECT COUNT(DISTINCT user_id) FROM sessions WHERE started_at >= :since"
                ),
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
    since = datetime.now(timezone.utc) - timedelta(days=days)
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
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
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
        "calls_per_hour": [
            {"hour": h, "count": c} for h, c in sorted(calls_per_hour.items())
        ],
        "top_users": [
            {"user_id": u, "count": c} for u, c in user_calls.most_common(5)
        ],
        "tutor_latency_per_hour": tutor_latency_per_hour,
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
    since_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
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

        r = await get_redis()
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
        "uptime_seconds": int((datetime.now(timezone.utc) - APP_BOOT_TS).total_seconds()),
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
        rps = await _prom_query(
            client, 'sum(rate(http_requests_total{job="fastapi"}[1m]))'
        )
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
