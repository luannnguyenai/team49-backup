#!/usr/bin/env bash
set -euo pipefail

task_definition_arn="${1:?task definition arn is required}"

: "${ECS_CLUSTER_NAME:?ECS_CLUSTER_NAME is required}"
: "${PRIVATE_SUBNET_IDS:?PRIVATE_SUBNET_IDS is required}"
: "${BACKEND_SECURITY_GROUP_ID:?BACKEND_SECURITY_GROUP_ID is required}"

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
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER_NAME" --tasks "$task_arn"

exit_code="$(aws ecs describe-tasks \
  --cluster "$ECS_CLUSTER_NAME" \
  --tasks "$task_arn" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"

if [ "$exit_code" != "0" ]; then
  echo "ECS task failed with exit code $exit_code: $task_arn" >&2
  exit 1
fi

echo "ECS task completed successfully: $task_arn"
echo "LAST_ECS_TASK_ARN=$task_arn" >> "${GITHUB_ENV:-/dev/null}"
