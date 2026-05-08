output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "app_runner_security_group_id" {
  value = aws_security_group.app_runner.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "cache_security_group_id" {
  value = aws_security_group.cache.id
}
