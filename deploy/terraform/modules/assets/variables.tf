variable "name_prefix" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "asset_prefix" {
  type = string
}

variable "enable_custom_domains" {
  type    = bool
  default = false
}

variable "hosted_zone_id" {
  type    = string
  default = ""
}

variable "assets_domain_name" {
  type    = string
  default = ""
}
