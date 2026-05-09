resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.identifier}-subnets"
  }
}

resource "aws_db_instance" "this" {
  identifier             = var.identifier
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = var.db_name
  username               = var.username
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false
  skip_final_snapshot    = false

  final_snapshot_identifier = "${var.identifier}-final-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  backup_retention_period     = 7
  backup_window               = "16:00-17:00"
  maintenance_window          = "Sun:17:00-Sun:18:00"
  manage_master_user_password = true

  # Trap A6: deletion_protection = true. Disable explicitly before destroy.
  deletion_protection = true

  performance_insights_enabled = false
  auto_minor_version_upgrade   = true
  apply_immediately            = true

  lifecycle {
    ignore_changes = [final_snapshot_identifier]
  }

  tags = {
    Name = var.identifier
  }
}
