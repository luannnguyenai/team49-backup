variable "budget_alert_email" {
  type = string
}

variable "name_prefix" {
  type    = string
  default = "a20-prod"
}

variable "backend_service_name" {
  type    = string
  default = "a20-backend"
}

variable "frontend_service_name" {
  type    = string
  default = "a20-frontend"
}

variable "log_retention_days" {
  type    = number
  default = 7
}
