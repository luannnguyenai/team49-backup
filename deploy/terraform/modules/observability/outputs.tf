output "budget_topic_arn" {
  value = aws_sns_topic.budget_alerts.arn
}
