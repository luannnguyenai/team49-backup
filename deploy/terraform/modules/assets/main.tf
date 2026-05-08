terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

locals {
  custom_assets_domain_enabled = var.enable_custom_domains && var.hosted_zone_id != "" && var.assets_domain_name != ""
}

resource "aws_s3_bucket" "assets" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudfront_origin_access_control" "assets" {
  name                              = "${var.name_prefix}-assets"
  description                       = "Origin access control for course assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "assets" {
  count    = local.custom_assets_domain_enabled ? 1 : 0
  provider = aws.us_east_1

  domain_name       = var.assets_domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "assets_validation" {
  for_each = local.custom_assets_domain_enabled ? {
    for dvo in aws_acm_certificate.assets[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id = var.hosted_zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "assets" {
  count    = local.custom_assets_domain_enabled ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.assets[0].arn
  validation_record_fqdns = [for record in aws_route53_record.assets_validation : record.fqdn]
}

resource "aws_cloudfront_distribution" "assets" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Course asset delivery"
  default_root_object = ""
  price_class         = "PriceClass_200"
  aliases             = local.custom_assets_domain_enabled ? [var.assets_domain_name] : []

  origin {
    domain_name              = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id                = "s3-assets-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.assets.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-assets-origin"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = local.custom_assets_domain_enabled ? aws_acm_certificate_validation.assets[0].certificate_arn : null
    cloudfront_default_certificate = local.custom_assets_domain_enabled ? false : true
    minimum_protocol_version       = local.custom_assets_domain_enabled ? "TLSv1.2_2021" : "TLSv1"
    ssl_support_method             = local.custom_assets_domain_enabled ? "sni-only" : null
  }
}

data "aws_iam_policy_document" "assets_bucket" {
  statement {
    sid = "AllowCloudFrontRead"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions = ["s3:GetObject"]

    resources = [
      "${aws_s3_bucket.assets.arn}/${var.asset_prefix}/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.assets.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id
  policy = data.aws_iam_policy_document.assets_bucket.json
}

resource "aws_route53_record" "assets_alias" {
  count = local.custom_assets_domain_enabled ? 1 : 0

  zone_id = var.hosted_zone_id
  name    = var.assets_domain_name
  type    = "A"

  alias {
    evaluate_target_health = false
    name                   = aws_cloudfront_distribution.assets.domain_name
    zone_id                = aws_cloudfront_distribution.assets.hosted_zone_id
  }
}
