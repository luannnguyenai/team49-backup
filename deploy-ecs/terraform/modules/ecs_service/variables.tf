variable "service_name" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "container_image" {
  type        = string
  description = "Full image URI including tag, e.g. 123.dkr.ecr.../a20-backend:abc123"
}

variable "container_port" {
  type = number
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "task_execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "log_group_name" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "environment" {
  type    = list(object({ name = string, value = string }))
  default = []
}

variable "secrets" {
  type    = list(object({ name = string, valueFrom = string }))
  default = []
}

variable "health_check_grace_period_seconds" {
  type    = number
  default = 60
}

variable "service_registry_arn" {
  type        = string
  default     = ""
  description = "Optional Cloud Map service ARN for ECS service discovery."
}

variable "service_registry_container_name" {
  type        = string
  default     = ""
  description = "Optional container name for Cloud Map registration."
}
