#!/usr/bin/env bash
set -euo pipefail

cluster_name="${1:?cluster name is required}"
service_name="${2:?service name is required}"
target_group_arn="${3:?target group arn is required}"

aws ecs wait services-stable --cluster "$cluster_name" --services "$service_name"

running_count="$(aws ecs describe-services \
  --cluster "$cluster_name" \
  --services "$service_name" \
  --query 'services[0].runningCount' \
  --output text)"

desired_count="$(aws ecs describe-services \
  --cluster "$cluster_name" \
  --services "$service_name" \
  --query 'services[0].desiredCount' \
  --output text)"

if [ "$running_count" != "$desired_count" ]; then
  echo "Service $service_name is stable but running count does not match desired count: $running_count/$desired_count" >&2
  exit 1
fi

healthy_count="$(aws elbv2 describe-target-health \
  --target-group-arn "$target_group_arn" \
  --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' \
  --output text)"

if [ "$healthy_count" = "0" ]; then
  echo "No healthy targets for $service_name target group $target_group_arn" >&2
  aws elbv2 describe-target-health --target-group-arn "$target_group_arn" >&2
  exit 1
fi

echo "Service $service_name stable with $healthy_count healthy target(s)."
