provider "aws" {
  region = "ap-southeast-1"

  default_tags {
    tags = {
      Project     = "a20"
      Environment = "prod"
      ManagedBy   = "terraform"
      Stack       = "terraform-state"
    }
  }
}
