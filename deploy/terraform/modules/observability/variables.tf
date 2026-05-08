variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "budget_alert_email" {
  type = string
}

variable "cloudfront_distribution_id" {
  type = string
}

variable "rds_instance_id" {
  type = string
}

variable "rds_free_storage_threshold_bytes" {
  type    = number
  default = 5368709120
}

variable "backend_service_name" {
  type    = string
  default = ""
}

variable "app_runner_service_arn" {
  type    = string
  default = ""
}

variable "nat_gateway_enabled" {
  type = bool
}
