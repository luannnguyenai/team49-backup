"""
core/observability.py
---------------------
Singleton LangFuse callback handler for LangChain / LangGraph.

Behaviour:
- If LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set → real handler that
  ships traces to LANGFUSE_HOST (default https://cloud.langfuse.com).
- If keys are missing or langfuse import fails → returns None. Callers must
  handle None and skip the callback (LLM still runs normally).

Usage:
    from src.core.observability import get_langfuse_handler

    handler = get_langfuse_handler()
    callbacks = [handler] if handler else []
    response = chain.invoke(input, config={"callbacks": callbacks, "metadata": {...}})
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from prometheus_client import Histogram

logger = logging.getLogger(__name__)

_TUTOR_METRIC_LABELS = ("route_type", "has_image")
_TUTOR_STREAM_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    30.0,
    60.0,
)

TUTOR_STREAM_FIRST_STATUS_SECONDS = Histogram(
    "tutor_stream_first_status_seconds",
    "Time from tutor request start to the first streamed status event.",
    _TUTOR_METRIC_LABELS,
    buckets=_TUTOR_STREAM_BUCKETS,
)

TUTOR_STREAM_FIRST_ANSWER_SECONDS = Histogram(
    "tutor_stream_first_answer_seconds",
    "Time from tutor request start to the first streamed answer chunk.",
    _TUTOR_METRIC_LABELS,
    buckets=_TUTOR_STREAM_BUCKETS,
)

TUTOR_STREAM_TOTAL_SECONDS = Histogram(
    "tutor_stream_total_seconds",
    "Total elapsed time for a tutor streaming request.",
    _TUTOR_METRIC_LABELS,
    buckets=_TUTOR_STREAM_BUCKETS,
)


def _normalize_tutor_route_type(route_type: str | None) -> str:
    normalized = (route_type or "unknown").strip().lower()
    if normalized in {"simple", "complex", "blocked", "error", "unknown"}:
        return normalized
    return "unknown"


def _tutor_metric_labels(route_type: str | None, has_image: bool) -> dict[str, str]:
    return {
        "route_type": _normalize_tutor_route_type(route_type),
        "has_image": "true" if has_image else "false",
    }


def observe_tutor_stream_first_status(
    duration_seconds: float,
    *,
    route_type: str | None,
    has_image: bool,
) -> None:
    TUTOR_STREAM_FIRST_STATUS_SECONDS.labels(
        **_tutor_metric_labels(route_type, has_image)
    ).observe(max(duration_seconds, 0.0))


def observe_tutor_stream_first_answer(
    duration_seconds: float,
    *,
    route_type: str | None,
    has_image: bool,
) -> None:
    TUTOR_STREAM_FIRST_ANSWER_SECONDS.labels(
        **_tutor_metric_labels(route_type, has_image)
    ).observe(max(duration_seconds, 0.0))


def observe_tutor_stream_total(
    duration_seconds: float,
    *,
    route_type: str | None,
    has_image: bool,
) -> None:
    TUTOR_STREAM_TOTAL_SECONDS.labels(
        **_tutor_metric_labels(route_type, has_image)
    ).observe(max(duration_seconds, 0.0))


@lru_cache(maxsize=1)
def get_langfuse_handler() -> Any | None:
    """Return a LangFuse CallbackHandler singleton, or None if not configured."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        logger.info(
            "LangFuse disabled: LANGFUSE_PUBLIC_KEY/SECRET_KEY not set "
            "(LLM calls will run without tracing)."
        )
        return None

    # Export keys for the LangFuse SDK (it reads env directly in v3).
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
    os.environ.setdefault("LANGFUSE_HOST", host)

    handler = None
    # Try LangFuse v3 first (works with langchain >= 1.x)
    try:
        from langfuse.langchain import CallbackHandler  # type: ignore

        handler = CallbackHandler()
        logger.info("LangFuse v3 callback handler initialised (host=%s).", host)
        return handler
    except Exception as exc_v3:
        logger.debug("LangFuse v3 init failed: %s", exc_v3)

    # Fall back to v2 callback module
    try:
        from langfuse.callback import CallbackHandler  # type: ignore

        handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("LangFuse v2 callback handler initialised (host=%s).", host)
        return handler
    except Exception as exc_v2:
        logger.warning("Failed to initialise LangFuse callback handler: %s", exc_v2)
        return None


def llm_callbacks() -> list[Any]:
    """Convenience: returns [handler] or []. Use as `callbacks=llm_callbacks()`."""
    handler = get_langfuse_handler()
    return [handler] if handler is not None else []
