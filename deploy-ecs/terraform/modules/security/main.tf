resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "ALB ingress from world, egress to frontend/backend"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-alb"
  }
}

resource "aws_security_group" "frontend" {
  name        = "${var.name_prefix}-frontend"
  description = "Frontend Fargate tasks - ingress from ALB only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-frontend"
  }
}

resource "aws_security_group" "backend" {
  name        = "${var.name_prefix}-backend"
  description = "Backend Fargate tasks - ingress from ALB only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-backend"
  }
}

resource "aws_security_group" "database" {
  name        = "${var.name_prefix}-database"
  description = "RDS - ingress from backend only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-database"
  }
}

resource "aws_security_group" "cache" {
  name        = "${var.name_prefix}-cache"
  description = "ElastiCache - ingress from backend only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name_prefix}-cache"
  }
}

# ----- ALB ingress -----
resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
  description       = "HTTP from world"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
  description       = "HTTPS from world"
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "ALB to anywhere (restricted by SG chain in practice)"
}

# ----- Frontend ingress (from ALB) -----
resource "aws_vpc_security_group_ingress_rule" "frontend_from_alb" {
  security_group_id            = aws_security_group.frontend.id
  ip_protocol                  = "tcp"
  from_port                    = var.frontend_container_port
  to_port                      = var.frontend_container_port
  referenced_security_group_id = aws_security_group.alb.id
  description                  = "Frontend port from ALB"
}

resource "aws_vpc_security_group_egress_rule" "frontend_all" {
  security_group_id = aws_security_group.frontend.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Frontend egress to ECR/Secrets/Logs via NAT"
}

# ----- Backend ingress (from ALB) -----
resource "aws_vpc_security_group_ingress_rule" "backend_from_alb" {
  security_group_id            = aws_security_group.backend.id
  ip_protocol                  = "tcp"
  from_port                    = var.backend_container_port
  to_port                      = var.backend_container_port
  referenced_security_group_id = aws_security_group.alb.id
  description                  = "Backend port from ALB"
}

resource "aws_vpc_security_group_egress_rule" "backend_all" {
  security_group_id = aws_security_group.backend.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Backend egress to RDS/Redis/ECR/Secrets/Logs"
}

# ----- Database ingress (from backend only) -----
resource "aws_vpc_security_group_ingress_rule" "database_from_backend" {
  security_group_id            = aws_security_group.database.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.backend.id
  description                  = "Postgres from backend"
}

# ----- Cache ingress (from backend only) -----
resource "aws_vpc_security_group_ingress_rule" "cache_from_backend" {
  security_group_id            = aws_security_group.cache.id
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.backend.id
  description                  = "Redis from backend"
}
