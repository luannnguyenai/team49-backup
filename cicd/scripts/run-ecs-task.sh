#!/usr/bin/env bash
set -euo pipefail

task_definition_arn="${1:?task definition arn is required}"

: "${ECS_CLUSTER_NAME:?ECS_CLUSTER_NAME is required}"
: "${PRIVATE_SUBNET_IDS:?PRIVATE_SUBNET_IDS is required}"
: "${BACKEND_SECURITY_GROUP_ID:?BACKEND_SECURITY_GROUP_ID is required}"
run_task_timeout_seconds="${RUN_TASK_TIMEOUT_SECONDS:-1800}"

task_arn="$(aws ecs run-task \
  --cluster "$ECS_CLUSTER_NAME" \
  --launch-type FARGATE \
  --task-definition "$task_definition_arn" \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_IDS],securityGroups=[$BACKEND_SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "$task_arn" ] || [ "$task_arn" = "None" ]; then
  echo "Failed to start ECS task for $task_definition_arn" >&2
  exit 1
fi

echo "Started task: $task_arn"

deadline=$((SECONDS + run_task_timeout_seconds))
last_status=""
while true; do
  last_status="$(aws ecs describe-tasks \
    --cluster "$ECS_CLUSTER_NAME" \
    --tasks "$task_arn" \
    --query 'tasks[0].lastStatus' \
    --output text)"

  if [ "$last_status" = "STOPPED" ]; then
    break
  fi

  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "ECS task timed out after ${run_task_timeout_seconds}s: $task_arn" >&2
    exit 124
  fi

  sleep 10
done

exit_code="$(aws ecs describe-tasks \
  --cluster "$ECS_CLUSTER_NAME" \
  --tasks "$task_arn" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"

if [ "$exit_code" != "0" ]; then
  echo "ECS task failed with exit code $exit_code: $task_arn" >&2
  if [ -n "${LOG_GROUP:-}" ]; then
    echo "Recent logs from ${LOG_GROUP}:" >&2
    aws logs describe-log-streams \
      --log-group-name "$LOG_GROUP" \
      --order-by LastEventTime \
      --descending \
      --max-items 3 \
      --query 'logStreams[].logStreamName' \
      --output text \
      | tr '\t' '\n' \
      | while IFS= read -r stream_name; do
          if [ -n "$stream_name" ]; then
            echo "--- $stream_name ---" >&2
            aws logs get-log-events \
              --log-group-name "$LOG_GROUP" \
              --log-stream-name "$stream_name" \
              --limit 50 \
              --query 'events[].message' \
              --output text >&2 || true
          fi
        done
  fi
  exit 1
fi

echo "ECS task completed successfully: $task_arn"
echo "LAST_ECS_TASK_ARN=$task_arn" >> "${GITHUB_ENV:-/dev/null}"
