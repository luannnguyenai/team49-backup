module "network" {
  source = "../../modules/network"

  name_prefix        = local.name_prefix
  enable_nat_gateway = var.enable_nat_gateway
}

module "assets" {
  source = "../../modules/assets"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix           = local.name_prefix
  bucket_name           = var.asset_bucket_name
  asset_prefix          = var.asset_prefix
  enable_custom_domains = var.enable_custom_domains
  hosted_zone_id        = var.hosted_zone_id
  assets_domain_name    = var.assets_domain_name
}

module "database" {
  source = "../../modules/database"

  identifier         = var.rds_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.rds_security_group_id
}

module "cache" {
  source = "../../modules/cache"

  identifier         = var.cache_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.cache_security_group_id
}

module "observability" {
  source = "../../modules/observability"

  project_name                     = var.project_name
  environment                      = var.environment
  budget_alert_email               = var.budget_alert_email
  cloudfront_distribution_id       = module.assets.cloudfront_distribution_id
  rds_instance_id                  = module.database.instance_id
  rds_free_storage_threshold_bytes = 5368709120
  backend_service_name             = var.backend_service_name
  app_runner_service_arn           = var.app_runner_service_arn
  nat_gateway_enabled              = var.enable_nat_gateway
}
