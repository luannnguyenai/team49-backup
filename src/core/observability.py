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

logger = logging.getLogger(__name__)


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
