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
