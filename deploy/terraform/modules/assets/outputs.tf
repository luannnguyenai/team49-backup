output "bucket_name" {
  value = aws_s3_bucket.assets.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.assets.arn
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.assets.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.assets.domain_name
}
