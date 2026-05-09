variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "backend_container_port" {
  type    = number
  default = 8000
}

variable "frontend_container_port" {
  type    = number
  default = 3000
}
