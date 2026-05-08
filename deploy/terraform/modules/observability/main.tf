locals {
  app_runner_alarm_enabled = var.backend_service_name != ""
}

resource "aws_sns_topic" "budget_alerts" {
  name = "${var.project_name}-${var.environment}-budget-alerts"
}

resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_email
}

resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project_name}-${var.environment}-monthly"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }
}

resource "aws_cloudwatch_metric_alarm" "cloudfront_bytes_downloaded" {
  alarm_name          = "${var.project_name}-${var.environment}-cloudfront-bytes-downloaded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BytesDownloaded"
  namespace           = "AWS/CloudFront"
  period              = 300
  statistic           = "Sum"
  threshold           = 53687091200
  alarm_description   = "Unexpectedly high CloudFront download volume."

  dimensions = {
    DistributionId = var.cloudfront_distribution_id
    Region         = "Global"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is high."

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-free-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.rds_free_storage_threshold_bytes
  alarm_description   = "RDS free storage space is low."

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "app_runner_5xx" {
  count = local.app_runner_alarm_enabled ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-apprunner-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5xxStatusResponses"
  namespace           = "AWS/AppRunner"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "App Runner backend is returning repeated 5xx responses."

  dimensions = {
    ServiceName = var.backend_service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "nat_gateway_review" {
  count = var.nat_gateway_enabled ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-nat-active-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ActiveConnectionCount"
  namespace           = "AWS/NATGateway"
  period              = 300
  statistic           = "Average"
  threshold           = 5000
  alarm_description   = "NAT gateway traffic is high enough to review spend."
}
