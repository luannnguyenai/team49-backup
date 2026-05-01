#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/srv/ai-learning/app}"
ENV_FILE="${ENV_FILE:-/srv/ai-learning/shared/.env.production}"

if [[ ! -d "$APP_ROOT" ]]; then
  echo "Missing APP_ROOT: $APP_ROOT" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ENV_FILE: $ENV_FILE" >&2
  exit 1
fi

cd "$APP_ROOT"

echo "Starting production deploy from $APP_ROOT"
docker compose --env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "Running migrations"
docker compose --env-file "$ENV_FILE" exec -T backend uv run alembic upgrade head

echo "Health checks"
docker compose --env-file "$ENV_FILE" exec -T backend python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8000/health').getcode() == 200"
docker compose --env-file "$ENV_FILE" exec -T frontend sh -lc "wget -qO- http://127.0.0.1:3000/api/health >/dev/null"

echo "Deploy finished"
