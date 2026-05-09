module "network" {
  source = "../../modules/network"

  name_prefix        = local.name_prefix
  enable_nat_gateway = var.enable_nat_gateway
}

module "security" {
  source = "../../modules/security"

  name_prefix             = local.name_prefix
  vpc_id                  = module.network.vpc_id
  backend_container_port  = var.backend_container_port
  frontend_container_port = var.frontend_container_port
}

module "ecr" {
  source = "../../modules/ecr"

  backend_repository_name  = var.backend_ecr_repo_name
  frontend_repository_name = var.frontend_ecr_repo_name
}

module "alb" {
  source = "../../modules/alb"

  name_prefix             = local.name_prefix
  vpc_id                  = module.network.vpc_id
  public_subnet_ids       = module.network.public_subnet_ids
  alb_security_group_id   = module.security.alb_security_group_id
  backend_container_port  = var.backend_container_port
  frontend_container_port = var.frontend_container_port
}

module "ecs_cluster" {
  source = "../../modules/ecs_cluster"

  cluster_name = var.cluster_name
}

module "database" {
  source = "../../modules/database"

  identifier         = var.rds_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.security.database_security_group_id
}

module "cache" {
  source = "../../modules/cache"

  identifier         = var.cache_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.security.cache_security_group_id
}

module "assets" {
  source = "../../modules/assets"

  bucket_name  = var.asset_bucket_name
  asset_prefix = var.asset_prefix
}

module "iam_oidc" {
  source = "../../modules/iam_oidc"

  github_repository = var.github_repository
  name_prefix       = local.name_prefix
  asset_bucket_arn  = module.assets.bucket_arn
  asset_prefix      = var.asset_prefix
}

module "observability" {
  source = "../../modules/observability"

  budget_alert_email    = var.budget_alert_email
  name_prefix           = local.name_prefix
  backend_service_name  = var.backend_service_name
  frontend_service_name = var.frontend_service_name
  log_retention_days    = 7
}

# ===========================================================================
# Stage 2 — ECS services. Only created after images are pushed to ECR.
# Set var.enable_services = true and provide backend_image, frontend_image,
# backend_secret_arn, then `terraform apply` again.
# ===========================================================================

module "backend_service" {
  count  = var.enable_services ? 1 : 0
  source = "../../modules/ecs_service"

  service_name            = var.backend_service_name
  cluster_arn             = module.ecs_cluster.cluster_arn
  container_image         = var.backend_image
  container_port          = var.backend_container_port
  cpu                     = var.backend_task_cpu
  memory                  = var.backend_task_memory
  desired_count           = 1
  task_execution_role_arn = module.iam_oidc.task_execution_role_arn
  task_role_arn           = module.iam_oidc.backend_task_role_arn
  subnet_ids              = module.network.private_subnet_ids
  security_group_id       = module.security.backend_security_group_id
  target_group_arn        = module.alb.backend_target_group_arn
  log_group_name          = "/ecs/${var.backend_service_name}"
  aws_region              = var.aws_region

  health_check_grace_period_seconds = 60

  environment = [
    { name = "PORT", value = tostring(var.backend_container_port) },
    { name = "DEBUG", value = "false" },
    { name = "LOG_LEVEL", value = "INFO" },
    { name = "ASSET_STORAGE_PROVIDER", value = "s3" },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "AWS_S3_BUCKET", value = var.asset_bucket_name },
    { name = "AWS_S3_PREFIX", value = var.asset_prefix },
    { name = "CLOUDFRONT_DOMAIN", value = module.assets.cloudfront_domain_name },
    { name = "FRONTEND_BASE_URL", value = "http://${module.alb.alb_dns_name}" },
    { name = "CORS_ORIGINS", value = "[\"http://${module.alb.alb_dns_name}\"]" }
  ]

  # Trap B4: secrets via secrets[] block, never environment[]
  secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.backend_secret_arn}:DATABASE_URL::" },
    { name = "REDIS_URL", valueFrom = "${var.backend_secret_arn}:REDIS_URL::" },
    { name = "SECRET_KEY", valueFrom = "${var.backend_secret_arn}:SECRET_KEY::" }
  ]

  depends_on = [module.observability]
}

module "frontend_service" {
  count  = var.enable_services ? 1 : 0
  source = "../../modules/ecs_service"

  service_name            = var.frontend_service_name
  cluster_arn             = module.ecs_cluster.cluster_arn
  container_image         = var.frontend_image
  container_port          = var.frontend_container_port
  cpu                     = var.frontend_task_cpu
  memory                  = var.frontend_task_memory
  desired_count           = 1
  task_execution_role_arn = module.iam_oidc.task_execution_role_arn
  task_role_arn           = module.iam_oidc.frontend_task_role_arn
  subnet_ids              = module.network.private_subnet_ids
  security_group_id       = module.security.frontend_security_group_id
  target_group_arn        = module.alb.frontend_target_group_arn
  log_group_name          = "/ecs/${var.frontend_service_name}"
  aws_region              = var.aws_region

  # Trap B2: Next.js standalone cold start ~90s
  health_check_grace_period_seconds = 120

  environment = [
    { name = "NODE_ENV", value = "production" },
    { name = "PORT", value = tostring(var.frontend_container_port) },
    # Trap A2: belt-and-suspenders. Dockerfile CMD already enforces this.
    { name = "HOSTNAME", value = "0.0.0.0" },
    { name = "NEXT_TELEMETRY_DISABLED", value = "1" }
  ]

  secrets = []

  depends_on = [module.observability]
}
