output "project_name" {
  value = var.project_name
}

output "environment" {
  value = var.environment
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "asset_bucket_name" {
  value = module.assets.bucket_name
}

output "cloudfront_domain_name" {
  value = module.assets.cloudfront_domain_name
}

output "rds_endpoint" {
  value = module.database.endpoint
}

output "cache_endpoint" {
  value = module.cache.primary_endpoint_address
}
