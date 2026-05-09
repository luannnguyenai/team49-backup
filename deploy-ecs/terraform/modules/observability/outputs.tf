output "backend_log_group_name" {
  value = aws_cloudwatch_log_group.backend.name
}

output "frontend_log_group_name" {
  value = aws_cloudwatch_log_group.frontend.name
}

output "migrate_log_group_name" {
  value = aws_cloudwatch_log_group.migrate.name
}
