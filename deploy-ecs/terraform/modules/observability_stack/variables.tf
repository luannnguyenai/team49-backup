variable "name_prefix" {
  description = "Resource name prefix (e.g. a20-prod)."
  type        = string
}

variable "aws_region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  description = "Private subnets for EFS mount targets and Fargate tasks."
  type        = list(string)
}

variable "cluster_arn" {
  description = "ECS cluster ARN to attach observability services to."
  type        = string
}

variable "task_execution_role_arn" {
  description = "Shared task execution role (must have access to ECR + observability secret + CloudWatch logs)."
  type        = string
}

variable "task_role_arn" {
  description = "Shared task role for observability tasks. Exporters need read access to backend secret for DATABASE_URL / REDIS_URL."
  type        = string
}

variable "alb_security_group_id" {
  description = "ALB security group. Grafana ingress will be from this SG on port 3000."
  type        = string
}

variable "alb_listener_arn" {
  description = "Existing ALB HTTP listener ARN. A listener rule for /grafana* will be attached."
  type        = string
}

variable "backend_security_group_id" {
  description = "Backend SG. Allows observability tasks to scrape /metrics on the backend port."
  type        = string
}

variable "backend_container_port" {
  description = "Backend container port (for /metrics scraping)."
  type        = number
  default     = 8000
}

variable "database_security_group_id" {
  description = "Postgres SG. Allow observability ingress for postgres_exporter."
  type        = string
}

variable "cache_security_group_id" {
  description = "Redis SG. Allow observability ingress for redis_exporter."
  type        = string
}

variable "backend_secret_arn" {
  description = "Backend secret ARN (Secrets Manager). Kept for backwards-compat; exporters now use observability_secret_arn."
  type        = string
}

variable "observability_secret_arn" {
  description = "Cleaned DSNs (POSTGRES_DSN without driver suffix, REDIS_URL) for exporters."
  type        = string
}

variable "image_prometheus" {
  description = "Full Prometheus image URI (ECR repo + tag)."
  type        = string
}

variable "image_loki" {
  type = string
}

variable "image_grafana" {
  type = string
}

variable "image_postgres_exporter" {
  type    = string
  default = "prometheuscommunity/postgres-exporter:v0.16.0"
}

variable "image_redis_exporter" {
  type    = string
  default = "oliver006/redis_exporter:v1.66.0"
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "task_cpu" {
  type    = number
  default = 256
}

variable "task_memory" {
  type    = number
  default = 512
}

variable "grafana_root_url_path" {
  description = "Sub-path Grafana is mounted under on the shared ALB."
  type        = string
  default     = "/grafana"
}
