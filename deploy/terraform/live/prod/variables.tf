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

variable "github_repository_url" {
  type = string
}

variable "github_branch" {
  type    = string
  default = "main"
}

variable "app_runner_connection_arn" {
  type      = string
  default   = ""
  sensitive = true
}

variable "manage_amplify_in_terraform" {
  type    = bool
  default = false
}

variable "amplify_app_id" {
  type    = string
  default = ""
}

variable "backend_service_name" {
  type    = string
  default = "a20-backend"
}

variable "frontend_app_name" {
  type    = string
  default = "a20-frontend"
}

variable "asset_bucket_name" {
  type    = string
  default = "a20-course-assets-prod"
}

variable "asset_prefix" {
  type    = string
  default = "courses"
}

variable "rds_identifier" {
  type    = string
  default = "a20-postgres-prod"
}

variable "cache_identifier" {
  type    = string
  default = "a20-redis-prod"
}

variable "budget_alert_email" {
  type = string
}

variable "hosted_zone_id" {
  type    = string
  default = ""
}

variable "frontend_domain_name" {
  type    = string
  default = ""
}

variable "backend_domain_name" {
  type    = string
  default = ""
}

variable "assets_domain_name" {
  type    = string
  default = ""
}

variable "app_runner_service_arn" {
  type    = string
  default = ""
}
