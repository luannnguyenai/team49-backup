# Note: Budget is created manually via AWS CLI in deploy bootstrap step,
# not by Terraform, so the budget guard exists before any infra apply.
# This module only manages CloudWatch log groups (trap B7 prevention).

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.backend_service_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.frontend_service_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/ecs/${var.backend_service_name}-migrate"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "bootstrap" {
  name              = "/ecs/${var.backend_service_name}-bootstrap"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "seed_core" {
  name              = "/ecs/${var.backend_service_name}-seed-core"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "sync_schema_v2" {
  name              = "/ecs/${var.backend_service_name}-sync-schema-v2"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "seed_accounts" {
  name              = "/ecs/${var.backend_service_name}-seed-accounts"
  retention_in_days = var.log_retention_days
}
