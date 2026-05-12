output "backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "observability_repository_urls" {
  description = "Map of observability repo name → ECR URL."
  value       = { for k, v in aws_ecr_repository.observability : k => v.repository_url }
}
