output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "frontend_security_group_id" {
  value = aws_security_group.frontend.id
}

output "backend_security_group_id" {
  value = aws_security_group.backend.id
}

output "database_security_group_id" {
  value = aws_security_group.database.id
}

output "cache_security_group_id" {
  value = aws_security_group.cache.id
}
