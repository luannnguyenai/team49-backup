"""
middleware/request_logger.py
----------------------------
Starlette middleware that emits one JSON line per HTTP request to
`logs/access.jsonl`. Promtail tails this file and ships to Loki.

Each line:
{
  "ts": "2026-05-02T08:21:55.123456+00:00",
  "method": "GET",
  "path": "/api/quiz/generate",
  "status": 200,
  "latency_ms": 142.55,
  "user_id": "<uuid or null>",
  "request_id": "<uuid4>",
  "client_ip": "127.0.0.1"
}

Notes:
- user_id is best-effort: pulled from request.state.user if a downstream auth
  dep set it, else from the JWT 'sub' claim, else null.
- The middleware is fail-safe: any logging error is swallowed so the request
  pipeline is never broken.
"""
from __future__ import annotations

import logging
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "access.jsonl"

_logger = logging.getLogger("admin.access")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    try:
        _handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=20 * 1024 * 1024,   # 20 MB
            backupCount=5,
            encoding="utf-8",
        )
        _handler.setFormatter(
            jsonlogger.JsonFormatter(
                "%(ts)s %(level)s %(message)s",
                rename_fields={"levelname": "level"},
                timestamp="ts",
            )
        )
        _logger.addHandler(_handler)
    except (PermissionError, OSError):
        # Fail gracefully in test/read-only environments
        pass


def _resolve_user_id(request: Request) -> str | None:
    user = getattr(request.state, "user", None)
    if user is not None:
        uid = getattr(user, "id", None)
        if uid is not None:
            return str(uid)
    # Best-effort decode of Authorization header without raising
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            from src.services.auth_service import decode_token  # local import to avoid cycles

            payload = decode_token(token)
            return getattr(payload, "sub", None)
        except Exception:
            return None
    return None


class AccessLogMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/metrics", "/health"}

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            try:
                _logger.info(
                    "http_request",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "latency_ms": latency_ms,
                        "user_id": _resolve_user_id(request),
                        "request_id": request_id,
                        "client_ip": request.client.host if request.client else None,
                    },
                )
            except Exception:
                # Never let logging break the request pipeline
                pass
