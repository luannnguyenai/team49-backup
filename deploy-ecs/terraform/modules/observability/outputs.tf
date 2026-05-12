output "backend_log_group_name" {
  value = aws_cloudwatch_log_group.backend.name
}

output "frontend_log_group_name" {
  value = aws_cloudwatch_log_group.frontend.name
}

output "migrate_log_group_name" {
  value = aws_cloudwatch_log_group.migrate.name
}

output "bootstrap_log_group_name" {
  value = aws_cloudwatch_log_group.bootstrap.name
}

output "seed_core_log_group_name" {
  value = aws_cloudwatch_log_group.seed_core.name
}

output "sync_schema_v2_log_group_name" {
  value = aws_cloudwatch_log_group.sync_schema_v2.name
}

output "seed_accounts_log_group_name" {
  value = aws_cloudwatch_log_group.seed_accounts.name
}
