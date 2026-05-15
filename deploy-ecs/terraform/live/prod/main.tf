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

  github_repository       = var.github_repository
  name_prefix             = local.name_prefix
  asset_bucket_arn        = module.assets.bucket_arn
  asset_prefix            = var.asset_prefix
  canonical_bundle_prefix = var.canonical_bundle_prefix
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

  service_name                    = var.backend_service_name
  cluster_arn                     = module.ecs_cluster.cluster_arn
  container_image                 = var.backend_image
  container_port                  = var.backend_container_port
  cpu                             = var.backend_task_cpu
  memory                          = var.backend_task_memory
  desired_count                   = 1
  task_execution_role_arn         = module.iam_oidc.task_execution_role_arn
  task_role_arn                   = module.iam_oidc.backend_task_role_arn
  subnet_ids                      = module.network.private_subnet_ids
  security_group_id               = module.security.backend_security_group_id
  target_group_arn                = module.alb.backend_target_group_arn
  log_group_name                  = "/ecs/${var.backend_service_name}"
  aws_region                      = var.aws_region
  service_registry_arn            = var.backend_service_registry_arn
  service_registry_container_name = var.backend_service_registry_arn != "" ? var.backend_service_name : ""

  health_check_grace_period_seconds = 60

  environment = [
    # Core runtime
    { name = "PORT", value = tostring(var.backend_container_port) },
    { name = "DEBUG", value = "false" },
    { name = "LOG_LEVEL", value = "INFO" },
    { name = "DB_ECHO", value = "false" },
    { name = "DB_POOL_SIZE", value = "10" },
    { name = "DB_MAX_OVERFLOW", value = "20" },

    # LangGraph checkpointer — skip setup() vì tables đã được alembic migrate.
    # Setup() trên psycopg với RDS hang vô hạn (advisory lock?). Fix: false.
    { name = "AGENT_GRAPH_CHECKPOINTER_SETUP", value = "false" },
    { name = "AGENT_GRAPH_CHECKPOINTER_BACKEND", value = "postgres" },

    # Asset delivery
    { name = "ASSET_STORAGE_PROVIDER", value = "s3" },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "AWS_DEFAULT_REGION", value = var.aws_region },
    { name = "AWS_S3_BUCKET", value = var.asset_bucket_name },
    { name = "AWS_S3_PREFIX", value = var.asset_prefix },
    { name = "AWS_CLOUDWATCH_LOG_GROUPS", value = join(",", compact([
      "/ecs/${var.backend_service_name}",
      "/ecs/${var.frontend_service_name}",
      "/ecs/${var.backend_service_name}-migrate",
      "/ecs/${var.backend_service_name}-bootstrap",
      "/ecs/${var.backend_service_name}-seed-core",
      "/ecs/${var.backend_service_name}-sync-schema-v2",
      "/ecs/${var.backend_service_name}-seed-accounts",
    ])) },
    { name = "CLOUDFRONT_DOMAIN", value = module.assets.cloudfront_domain_name },
    { name = "ASSET_URL_EXPIRE_SECONDS", value = "900" },

    # CORS / frontend
    { name = "FRONTEND_BASE_URL", value = "http://${module.alb.alb_dns_name}" },
    { name = "CORS_ORIGINS", value = "[\"http://${module.alb.alb_dns_name}\"]" },

    # Auth
    { name = "ALGORITHM", value = "HS256" },
    { name = "ACCESS_TOKEN_EXPIRE_MINUTES", value = "30" },
    { name = "REFRESH_TOKEN_EXPIRE_DAYS", value = "7" },
    { name = "RATE_LIMIT_LOGIN_PER_MINUTE", value = "5" },
    { name = "PASSWORD_RESET_TOKEN_TTL_MINUTES", value = "30" },

    # LLM provider
    { name = "MODEL_PROVIDER", value = "openai" },
    { name = "DEFAULT_MODEL", value = "gpt-5.4-mini" },
    { name = "FAST_MODEL", value = "gpt-5.4-nano" },
    { name = "GEMINI_REQUESTS_PER_MINUTE", value = "15" },
    { name = "MODEL_EXTRA_KWARGS", value = "{}" },
    { name = "LLM_REQUEST_TIMEOUT_SECONDS", value = "30" },
    { name = "LLM_MAX_RETRIES", value = "1" },
    { name = "CHAT_MODEL_HEALTH_TIMEOUT_SECONDS", value = "3" },
    { name = "GUARDRAIL_ROUTER_BASE_URL", value = "https://router.a20-app-049.io.vn/v1" },
    { name = "GUARDRAIL_ROUTER_MODEL", value = "guardrail-router-merged" },
    { name = "GUARDRAIL_ROUTER_TIMEOUT_SECONDS", value = "10.0" },
    { name = "GUARDRAIL_ROUTER_UNHEALTHY_COOLDOWN_SECONDS", value = "60.0" },
    { name = "GUARDRAIL_ROUTER_MAX_TOKENS", value = "96" },

    # Langfuse non-secret
    { name = "LANGFUSE_BASE_URL", value = "https://cloud.langfuse.com" },

    # Observability
    { name = "PROMETHEUS_URL", value = "http://prometheus.obs.a20-prod.internal:9090" },
    { name = "LOKI_URL", value = "http://loki.obs.a20-prod.internal:3100" },

    # Knowledge graph
    { name = "KG_PHASE", value = "0" },
    { name = "KG_MASTERY_SKIP_THRESHOLD", value = "0.7" },
    { name = "KG_MASTERY_REVIEW_THRESHOLD", value = "0.4" },
    { name = "KG_SHORTCUT_MASTERY_THRESHOLD", value = "0.8" },
    { name = "KG_SHORTCUT_HOURS_FACTOR", value = "0.4" },
    { name = "KG_PATH_WEEK_BUFFER", value = "0.2" },
    { name = "KG_BUCKET_WEIGHTS", value = "{\"easy\":1.0,\"medium\":1.3,\"hard\":1.6}" },
    { name = "KG_RECSYS_WEIGHTS", value = "{\"mastery_gap\":0.35,\"prereq_ready\":0.25,\"transfer_boost\":0.2,\"goal_distance\":0.15,\"freshness\":0.05}" },

    # Canonical runtime feature flags
    { name = "WRITE_GOAL_PREFERENCES_ENABLED", value = "true" },
    { name = "WRITE_LEARNER_MASTERY_KP_ENABLED", value = "true" },
    { name = "WRITE_WAIVED_UNITS_ENABLED", value = "true" },
    { name = "WRITE_PLANNER_AUDIT_ENABLED", value = "true" },
    { name = "READ_GOAL_PREFERENCES_ENABLED", value = "true" },
    { name = "READ_LEARNER_MASTERY_KP_ENABLED", value = "true" },
    { name = "READ_CANONICAL_QUESTIONS_ENABLED", value = "true" },
    { name = "WRITE_CANONICAL_INTERACTIONS_ENABLED", value = "true" },
    { name = "READ_CANONICAL_PLANNER_ENABLED", value = "true" },

    # Placement / IRT
    { name = "COLD_START_MODE", value = "spread_by_prior" },
    { name = "IRT_MIN_AVG_RESPONSES", value = "200" },
    { name = "IRT_MIN_CALIBRATED_RATIO", value = "0.8" },
    { name = "IRT_MAX_MEDIAN_SE_B", value = "0.3" },
    { name = "IRT_EXPOSURE_CAP_HOURS", value = "24" },
    { name = "IRT_USE_2PL", value = "false" },

    # AI prompt logging
    { name = "AI_LOG_SERVER", value = "https://ai-logs.note.transformerlabs.ai/api/ingest" },
    { name = "AI_LOG_DIR", value = ".ai-log" },

    # Email
    { name = "EMAIL_FROM", value = "eddiedepunnie@gmail.com" }
  ]

  # Trap B4: secrets via secrets[] block, never environment[]
  secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.backend_secret_arn}:DATABASE_URL::" },
    { name = "REDIS_URL", valueFrom = "${var.backend_secret_arn}:REDIS_URL::" },
    { name = "SECRET_KEY", valueFrom = "${var.backend_secret_arn}:SECRET_KEY::" },
    { name = "OPENAI_API_KEY", valueFrom = "${var.backend_secret_arn}:OPENAI_API_KEY::" },
    { name = "ANTHROPIC_API_KEY", valueFrom = "${var.backend_secret_arn}:ANTHROPIC_API_KEY::" },
    { name = "GEMINI_API_KEY", valueFrom = "${var.backend_secret_arn}:GEMINI_API_KEY::" },
    { name = "LANGFUSE_SECRET_KEY", valueFrom = "${var.backend_secret_arn}:LANGFUSE_SECRET_KEY::" },
    { name = "LANGFUSE_PUBLIC_KEY", valueFrom = "${var.backend_secret_arn}:LANGFUSE_PUBLIC_KEY::" },
    { name = "GMAIL_APP_PASSWORD", valueFrom = "${var.backend_secret_arn}:GMAIL_APP_PASSWORD::" },
    { name = "AI_LOG_API_KEY", valueFrom = "${var.backend_secret_arn}:AI_LOG_API_KEY::" },
    { name = "ADMIN_TOKEN", valueFrom = "${var.backend_secret_arn}:ADMIN_TOKEN::" }
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

# ===========================================================================
# Stage 3 — Observability stack (Prometheus / Loki / Grafana / exporters).
# Enable with: -var=enable_observability_stack=true plus image_* and password vars.
# ===========================================================================
module "observability_stack" {
  count  = var.enable_observability_stack ? 1 : 0
  source = "../../modules/observability_stack"

  name_prefix             = local.name_prefix
  aws_region              = var.aws_region
  vpc_id                  = module.network.vpc_id
  private_subnet_ids      = module.network.private_subnet_ids
  cluster_arn             = module.ecs_cluster.cluster_arn
  task_execution_role_arn = module.iam_oidc.task_execution_role_arn
  task_role_arn           = module.iam_oidc.backend_task_role_arn

  alb_security_group_id      = module.security.alb_security_group_id
  alb_listener_arn           = var.enable_custom_domains ? var.custom_https_listener_arn : module.alb.http_listener_arn
  backend_security_group_id  = module.security.backend_security_group_id
  backend_container_port     = var.backend_container_port
  database_security_group_id = module.security.database_security_group_id
  cache_security_group_id    = module.security.cache_security_group_id

  backend_secret_arn       = var.backend_secret_arn
  observability_secret_arn = "arn:aws:secretsmanager:${var.aws_region}:116533674568:secret:a20/prod/observability-Ea5JOh"

  image_prometheus = var.image_prometheus
  image_loki       = var.image_loki
  image_grafana    = var.image_grafana

  depends_on = [module.alb, module.database, module.cache]
}
