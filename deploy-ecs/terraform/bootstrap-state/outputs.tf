output "state_bucket_name" {
  value = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_region" {
  value = "ap-southeast-1"
}
