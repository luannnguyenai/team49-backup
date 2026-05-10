variable "project_name" {
  type    = string
  default = "a20"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "domain_name" {
  type    = string
  default = "example.com"
}

variable "enable_custom_domains" {
  type    = bool
  default = false
}

variable "enable_nat_gateway" {
  type    = bool
  default = true
}

variable "cluster_name" {
  type = string
}

variable "backend_service_name" {
  type = string
}

variable "frontend_service_name" {
  type = string
}

variable "backend_task_cpu" {
  type = number
}

variable "backend_task_memory" {
  type = number
}

variable "frontend_task_cpu" {
  type = number
}

variable "frontend_task_memory" {
  type = number
}

variable "backend_container_port" {
  type = number
}

variable "frontend_container_port" {
  type = number
}

variable "backend_ecr_repo_name" {
  type = string
}

variable "frontend_ecr_repo_name" {
  type = string
}

variable "asset_bucket_name" {
  type = string
}

variable "asset_prefix" {
  type = string
}

variable "rds_identifier" {
  type = string
}

variable "cache_identifier" {
  type = string
}

variable "budget_alert_email" {
  type = string
}

variable "github_repository" {
  type        = string
  description = "owner/repo, e.g. edward1503/a20-app"
}

# ----- Stage 2 variables (only used when enable_services = true) -----

variable "enable_services" {
  type        = bool
  default     = false
  description = "Stage 1: false (foundation only). Stage 2: true (after pushing images to ECR)."
}

variable "backend_image" {
  type        = string
  default     = ""
  description = "Full backend image URI with tag. Required when enable_services=true."
}

variable "frontend_image" {
  type        = string
  default     = ""
  description = "Full frontend image URI with tag. Required when enable_services=true."
}

variable "backend_secret_arn" {
  type        = string
  default     = ""
  description = "Secrets Manager ARN containing DATABASE_URL, REDIS_URL, SECRET_KEY. Required when enable_services=true."
}
