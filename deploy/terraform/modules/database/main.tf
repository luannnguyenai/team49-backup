resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "this" {
  identifier                   = var.identifier
  engine                       = "postgres"
  engine_version               = "16.13"
  instance_class               = var.instance_class
  allocated_storage            = var.allocated_storage
  max_allocated_storage        = var.max_allocated_storage
  storage_type                 = "gp3"
  db_subnet_group_name         = aws_db_subnet_group.this.name
  vpc_security_group_ids       = [var.security_group_id]
  db_name                      = var.database_name
  username                     = var.master_username
  manage_master_user_password  = true
  publicly_accessible          = false
  backup_retention_period      = 7
  backup_window                = "17:00-18:00"
  maintenance_window           = "sun:18:00-sun:19:00"
  deletion_protection          = true
  skip_final_snapshot          = false
  final_snapshot_identifier    = "${var.identifier}-final"
  performance_insights_enabled = true
  auto_minor_version_upgrade   = true
  multi_az                     = false
  storage_encrypted            = true
  copy_tags_to_snapshot        = true
}
