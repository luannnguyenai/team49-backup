output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "alb_arn" {
  value = module.alb.alb_arn
}

output "backend_target_group_arn" {
  value = module.alb.backend_target_group_arn
}

output "frontend_target_group_arn" {
  value = module.alb.frontend_target_group_arn
}

output "ecs_cluster_name" {
  value = module.ecs_cluster.cluster_name
}

output "ecs_cluster_arn" {
  value = module.ecs_cluster.cluster_arn
}

output "backend_repository_url" {
  value = module.ecr.backend_repository_url
}

output "frontend_repository_url" {
  value = module.ecr.frontend_repository_url
}

output "asset_bucket_name" {
  value = module.assets.bucket_name
}

output "asset_bucket_arn" {
  value = module.assets.bucket_arn
}

output "cloudfront_domain_name" {
  value = module.assets.cloudfront_domain_name
}

output "cloudfront_distribution_id" {
  value = module.assets.cloudfront_distribution_id
}

output "rds_endpoint" {
  value = module.database.endpoint
}

output "rds_master_user_secret_arn" {
  value = module.database.master_user_secret_arn
}

output "redis_endpoint" {
  value = module.cache.primary_endpoint_address
}

output "deploy_role_arn" {
  value = module.iam_oidc.deploy_role_arn
}

output "task_execution_role_arn" {
  value = module.iam_oidc.task_execution_role_arn
}

output "backend_task_role_arn" {
  value = module.iam_oidc.backend_task_role_arn
}

output "frontend_task_role_arn" {
  value = module.iam_oidc.frontend_task_role_arn
}

output "backend_security_group_id" {
  value = module.security.backend_security_group_id
}

output "frontend_security_group_id" {
  value = module.security.frontend_security_group_id
}

output "backend_log_group_name" {
  value = module.observability.backend_log_group_name
}

output "frontend_log_group_name" {
  value = module.observability.frontend_log_group_name
}

output "migrate_log_group_name" {
  value = module.observability.migrate_log_group_name
}

# Observability stack (Stage 3, present only when enabled)
output "observability_repository_urls" {
  value = module.ecr.observability_repository_urls
}

output "grafana_url" {
  description = "Grafana endpoint on the shared ALB (sub-path). null when stack disabled."
  value       = var.enable_observability_stack ? "http://${module.alb.alb_dns_name}${module.observability_stack[0].grafana_path}" : null
}
