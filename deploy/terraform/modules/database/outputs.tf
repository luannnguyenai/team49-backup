output "instance_id" {
  value = aws_db_instance.this.id
}

output "arn" {
  value = aws_db_instance.this.arn
}

output "endpoint" {
  value = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "master_user_secret_arn" {
  value = aws_db_instance.this.master_user_secret[0].secret_arn
}
