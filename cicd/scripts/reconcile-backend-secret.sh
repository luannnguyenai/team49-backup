#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 2
  fi
}

require_env AWS_REGION
require_env BACKEND_SECRET_ARN
require_env PRODUCTION_FRONTEND_URL
require_env PRODUCTION_BACKEND_URL

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to reconcile the backend secret." >&2
  exit 2
fi

db_instance_id="${PRODUCTION_DB_INSTANCE_IDENTIFIER:-a20-postgres-prod}"
redis_cluster_id="${PRODUCTION_REDIS_CLUSTER_ID:-a20-redis-prod}"
prometheus_url="${PRODUCTION_PROMETHEUS_URL:-http://prometheus.obs.a20-prod.internal:9090}"
grafana_host="${NEXT_PUBLIC_GRAFANA_HOST:-}"

if [ -z "$grafana_host" ]; then
  grafana_host="/grafana"
elif [[ "$grafana_host" == http://* ]] && [[ "${PRODUCTION_FRONTEND_URL:-}" == https://* ]]; then
  grafana_host="/grafana"
fi

rds_json="$(aws rds describe-db-instances \
  --db-instance-identifier "$db_instance_id" \
  --region "$AWS_REGION" \
  --output json)"

db_host="$(jq -r '.DBInstances[0].Endpoint.Address' <<<"$rds_json")"
db_port="$(jq -r '.DBInstances[0].Endpoint.Port' <<<"$rds_json")"
db_name="$(jq -r '.DBInstances[0].DBName' <<<"$rds_json")"
rds_secret_arn="$(jq -r '.DBInstances[0].MasterUserSecret.SecretArn' <<<"$rds_json")"

if [ -z "$db_host" ] || [ "$db_host" = "null" ] || [ -z "$rds_secret_arn" ] || [ "$rds_secret_arn" = "null" ]; then
  echo "Unable to resolve production RDS endpoint or managed secret." >&2
  exit 3
fi

rds_secret="$(
  aws secretsmanager get-secret-value \
    --secret-id "$rds_secret_arn" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text
)"

db_user="$(jq -r '.username' <<<"$rds_secret")"
db_password="$(jq -r '.password' <<<"$rds_secret")"

db_user_escaped="$(jq -rn --arg v "$db_user" '$v|@uri')"
db_password_escaped="$(jq -rn --arg v "$db_password" '$v|@uri')"

redis_json="$(aws elasticache describe-cache-clusters \
  --cache-cluster-id "$redis_cluster_id" \
  --show-cache-node-info \
  --region "$AWS_REGION" \
  --output json)"

redis_host="$(jq -r '.CacheClusters[0].CacheNodes[0].Endpoint.Address' <<<"$redis_json")"
redis_port="$(jq -r '.CacheClusters[0].CacheNodes[0].Endpoint.Port' <<<"$redis_json")"

if [ -z "$redis_host" ] || [ "$redis_host" = "null" ]; then
  echo "Unable to resolve production Redis endpoint." >&2
  exit 3
fi

current_secret="$(
  aws secretsmanager get-secret-value \
    --secret-id "$BACKEND_SECRET_ARN" \
    --region "$AWS_REGION" \
    --query SecretString \
    --output text
)"

new_secret="$(jq \
  --arg db_host "$db_host" \
  --arg db_port "$db_port" \
  --arg db_name "$db_name" \
  --arg db_user "$db_user" \
  --arg db_password "$db_password" \
  --arg db_user_escaped "$db_user_escaped" \
  --arg db_password_escaped "$db_password_escaped" \
  --arg redis_host "$redis_host" \
  --arg redis_port "$redis_port" \
  --arg frontend_url "$PRODUCTION_FRONTEND_URL" \
  --arg backend_url "$PRODUCTION_BACKEND_URL" \
  --arg prometheus_url "$prometheus_url" \
  --arg grafana_host "$grafana_host" \
  '
  .POSTGRES_HOST = $db_host
  | .POSTGRES_PORT = $db_port
  | .POSTGRES_DB = $db_name
  | .POSTGRES_USER = $db_user
  | .POSTGRES_PASSWORD = $db_password
  | .DATABASE_URL = ("postgresql+asyncpg://" + $db_user_escaped + ":" + $db_password_escaped + "@" + $db_host + ":" + $db_port + "/" + $db_name)
  | .REDIS_URL = ("redis://" + $redis_host + ":" + $redis_port + "/0")
  | .FRONTEND_BASE_URL = $frontend_url
  | .NEXT_PUBLIC_API_URL = $backend_url
  | .API_INTERNAL_URL = $backend_url
  | .NEXT_PUBLIC_GRAFANA_HOST = $grafana_host
  | .PROMETHEUS_URL = $prometheus_url
  | .CORS_ORIGINS = ([$frontend_url] | tojson)
  ' <<<"$current_secret")"

violations="$(
  jq -r '
    to_entries[]
    | select((.value | type) == "string")
    | select(.key as $k | ["DATABASE_URL","REDIS_URL","FRONTEND_BASE_URL","NEXT_PUBLIC_API_URL","API_INTERNAL_URL","NEXT_PUBLIC_GRAFANA_HOST","PROMETHEUS_URL","CORS_ORIGINS","POSTGRES_HOST"] | index($k))
    | select(.value | test("localhost|127\\.0\\.0\\.1"))
    | "\(.key)=\(.value)"
  ' <<<"$new_secret"
)"

if [ -n "$violations" ]; then
  echo "Backend secret still contains localhost loopback values:" >&2
  echo "$violations" >&2
  exit 4
fi

tmp_secret="$(mktemp)"
trap 'rm -f "$tmp_secret"' EXIT
printf '%s' "$new_secret" > "$tmp_secret"

aws secretsmanager update-secret \
  --secret-id "$BACKEND_SECRET_ARN" \
  --region "$AWS_REGION" \
  --secret-string "file://$tmp_secret" \
  >/dev/null

echo "Reconciled backend secret for DB, Redis, frontend, and observability endpoints."
