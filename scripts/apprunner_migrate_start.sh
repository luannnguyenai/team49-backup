#!/bin/sh
set -eu

uv run alembic upgrade head
exec uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
