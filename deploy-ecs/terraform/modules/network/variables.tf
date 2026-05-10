variable "name_prefix" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "availability_zone_count" {
  type    = number
  default = 2
}

variable "enable_nat_gateway" {
  type = bool
}
