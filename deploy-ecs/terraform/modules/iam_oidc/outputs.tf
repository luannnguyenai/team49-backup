output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}

output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}

output "task_execution_role_arn" {
  value = aws_iam_role.task_execution.arn
}

output "backend_task_role_arn" {
  value = aws_iam_role.backend_task.arn
}

output "frontend_task_role_arn" {
  value = aws_iam_role.frontend_task.arn
}
