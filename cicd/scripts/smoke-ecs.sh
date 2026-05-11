#!/usr/bin/env bash
set -euo pipefail

mode="${1:?smoke mode is required: backend|frontend|db|cloudfront}"

http_code() {
  local url="$1"
  curl --silent --show-error --location --output /tmp/smoke-body --write-out "%{http_code}" "$url"
}

require_200() {
  local url="$1"
  local code
  code="$(http_code "$url")"
  if [ "$code" != "200" ]; then
    echo "Smoke failed: $url returned $code" >&2
    cat /tmp/smoke-body >&2 || true
    exit 1
  fi
  echo "Smoke passed: $url"
}

case "$mode" in
  backend)
    : "${PRODUCTION_BACKEND_URL:?PRODUCTION_BACKEND_URL is required}"
    require_200 "${PRODUCTION_BACKEND_URL%/}/health"
    ;;
  frontend)
    : "${PRODUCTION_FRONTEND_URL:?PRODUCTION_FRONTEND_URL is required}"
    require_200 "${PRODUCTION_FRONTEND_URL%/}/"
    ;;
  db)
    : "${PRODUCTION_BACKEND_URL:?PRODUCTION_BACKEND_URL is required}"
    : "${SMOKE_DB_ROUTE:?SMOKE_DB_ROUTE is required}"
    require_200 "${PRODUCTION_BACKEND_URL%/}${SMOKE_DB_ROUTE}"
    ;;
  cloudfront)
    : "${CLOUDFRONT_SMOKE_URL:?CLOUDFRONT_SMOKE_URL is required}"
    code="$(curl --silent --show-error --location --range 0-1023 --output /tmp/smoke-body --write-out "%{http_code}" "$CLOUDFRONT_SMOKE_URL")"
    if [ "$code" != "200" ] && [ "$code" != "206" ]; then
      echo "CloudFront smoke failed: $CLOUDFRONT_SMOKE_URL returned $code" >&2
      exit 1
    fi
    echo "CloudFront smoke passed: $CLOUDFRONT_SMOKE_URL returned $code"
    ;;
  *)
    echo "Unknown smoke mode: $mode" >&2
    exit 2
    ;;
esac
