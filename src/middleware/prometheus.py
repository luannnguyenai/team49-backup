"""
middleware/prometheus.py
------------------------
Wires up `prometheus-fastapi-instrumentator` to expose:
  - http_requests_total{method,handler,status}
  - http_request_duration_seconds_{count,sum,bucket}{...}
at GET /metrics for Prometheus scrape.

Custom counters/histograms specific to LLM and admin domains can be added
in src/core/observability.py and imported where they fire.
"""
from __future__ import annotations

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_prometheus(app: FastAPI) -> Instrumentator:
    """Attach Prometheus instrumentator to the given FastAPI app and expose /metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/metrics", "/health"],
    )
    instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["ops"],
    )
    return instrumentator
