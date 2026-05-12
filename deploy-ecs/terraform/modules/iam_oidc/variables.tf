variable "github_repository" {
  type        = string
  description = "owner/repo format, e.g. edward1503/a20-app"
}

variable "name_prefix" {
  type    = string
  default = "a20-prod"
}

variable "asset_bucket_arn" {
  type    = string
  default = ""
}

variable "asset_prefix" {
  type    = string
  default = "courses"
}

variable "canonical_bundle_prefix" {
  type    = string
  default = "canonical-bundles"
}
