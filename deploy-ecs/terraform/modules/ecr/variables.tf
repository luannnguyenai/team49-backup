variable "backend_repository_name" {
  type = string
}

variable "frontend_repository_name" {
  type = string
}

variable "observability_repository_names" {
  description = "Additional ECR repositories for the observability stack."
  type        = list(string)
  default     = ["a20-prometheus", "a20-loki", "a20-grafana"]
}
