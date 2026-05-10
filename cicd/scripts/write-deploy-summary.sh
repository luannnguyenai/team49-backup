#!/usr/bin/env bash
set -euo pipefail

summary_path="${GITHUB_STEP_SUMMARY:-/tmp/deploy-summary.md}"

{
  echo "## ECS Production Deploy"
  echo
  echo "| Item | Value |"
  echo "|---|---|"
  echo "| Commit | ${GITHUB_SHA:-unknown} |"
  echo "| Backend image | ${BACKEND_IMAGE:-not deployed} |"
  echo "| Frontend image | ${FRONTEND_IMAGE:-not deployed} |"
  echo "| Backend task definition | ${BACKEND_TASK_DEFINITION_ARN:-not deployed} |"
  echo "| Frontend task definition | ${FRONTEND_TASK_DEFINITION_ARN:-not deployed} |"
  echo "| Migrate task definition | ${MIGRATE_TASK_DEFINITION_ARN:-not run} |"
  echo "| Bootstrap task definition | ${BOOTSTRAP_TASK_DEFINITION_ARN:-not run} |"
  echo "| Last one-off task | ${LAST_ECS_TASK_ARN:-none} |"
  echo "| Backend URL | ${PRODUCTION_BACKEND_URL:-unset} |"
  echo "| Frontend URL | ${PRODUCTION_FRONTEND_URL:-unset} |"
} >> "$summary_path"
