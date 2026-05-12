# =============================================================================
# Observability stack on ECS Fargate: Prometheus, Loki, Grafana, exporters.
# Storage: shared EFS with 3 access points.
# Service discovery: Cloud Map private DNS namespace obs.a20.internal.
# Exposure: Grafana via existing ALB at /grafana/* (sub-path mode).
# =============================================================================

locals {
  ns = var.name_prefix
}

# ----- Security group -----
resource "aws_security_group" "obs" {
  name        = "${local.ns}-observability"
  description = "Observability stack (Prometheus, Loki, Grafana, exporters)"
  vpc_id      = var.vpc_id

  tags = { Name = "${local.ns}-observability" }
}

# Allow ingress from itself (Grafana → Prometheus/Loki, Prometheus → exporters)
resource "aws_vpc_security_group_ingress_rule" "obs_self" {
  for_each                     = toset(["9090", "3100", "3000", "9187", "9121"])
  security_group_id            = aws_security_group.obs.id
  ip_protocol                  = "tcp"
  from_port                    = tonumber(each.value)
  to_port                      = tonumber(each.value)
  referenced_security_group_id = aws_security_group.obs.id
  description                  = "obs self ingress :${each.value}"
}

# Grafana port from ALB
resource "aws_vpc_security_group_ingress_rule" "grafana_from_alb" {
  security_group_id            = aws_security_group.obs.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = var.alb_security_group_id
  description                  = "Grafana from ALB"
}

resource "aws_vpc_security_group_egress_rule" "obs_all" {
  security_group_id = aws_security_group.obs.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  description       = "obs egress to anywhere (ECR/Secrets/Logs/RDS/Redis/backend)"
}

# Backend SG: allow obs to scrape /metrics
resource "aws_vpc_security_group_ingress_rule" "backend_from_obs" {
  security_group_id            = var.backend_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = var.backend_container_port
  to_port                      = var.backend_container_port
  referenced_security_group_id = aws_security_group.obs.id
  description                  = "Backend /metrics scrape from observability"
}

# DB SG: allow postgres_exporter
resource "aws_vpc_security_group_ingress_rule" "db_from_obs" {
  security_group_id            = var.database_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.obs.id
  description                  = "Postgres from observability exporter"
}

# Cache SG: allow redis_exporter
resource "aws_vpc_security_group_ingress_rule" "cache_from_obs" {
  security_group_id            = var.cache_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.obs.id
  description                  = "Redis from observability exporter"
}

# ----- EFS for persistent storage -----
resource "aws_security_group" "efs" {
  name        = "${local.ns}-obs-efs"
  description = "EFS for observability stack"
  vpc_id      = var.vpc_id

  tags = { Name = "${local.ns}-obs-efs" }
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_obs" {
  security_group_id            = aws_security_group.efs.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = aws_security_group.obs.id
  description                  = "NFS from observability tasks"
}

resource "aws_efs_file_system" "obs" {
  creation_token = "${local.ns}-obs"
  encrypted      = true

  tags = { Name = "${local.ns}-obs" }
}

resource "aws_efs_mount_target" "obs" {
  for_each        = toset(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.obs.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "prometheus" {
  file_system_id = aws_efs_file_system.obs.id

  posix_user {
    uid = 65534
    gid = 65534
  }

  root_directory {
    path = "/prometheus"
    creation_info {
      owner_uid   = 65534
      owner_gid   = 65534
      permissions = "0755"
    }
  }
}

resource "aws_efs_access_point" "loki" {
  file_system_id = aws_efs_file_system.obs.id

  posix_user {
    uid = 10001
    gid = 10001
  }

  root_directory {
    path = "/loki"
    creation_info {
      owner_uid   = 10001
      owner_gid   = 10001
      permissions = "0755"
    }
  }
}

resource "aws_efs_access_point" "grafana" {
  file_system_id = aws_efs_file_system.obs.id

  posix_user {
    uid = 472
    gid = 472
  }

  root_directory {
    path = "/grafana"
    creation_info {
      owner_uid   = 472
      owner_gid   = 472
      permissions = "0755"
    }
  }
}

# ----- Service discovery (private DNS) -----
resource "aws_service_discovery_private_dns_namespace" "obs" {
  name        = "obs.${local.ns}.internal"
  description = "Observability internal DNS"
  vpc         = var.vpc_id
}

resource "aws_service_discovery_service" "this" {
  for_each = toset(["prometheus", "loki", "grafana", "postgres-exporter", "redis-exporter"])
  name     = each.value

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.obs.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ----- CloudWatch log groups -----
resource "aws_cloudwatch_log_group" "obs" {
  for_each          = toset(["prometheus", "loki", "grafana", "postgres-exporter", "redis-exporter"])
  name              = "/ecs/${local.ns}-${each.value}"
  retention_in_days = var.log_retention_days
}

# =============================================================================
# Task definitions
# =============================================================================

# Prometheus
resource "aws_ecs_task_definition" "prometheus" {
  family                   = "${local.ns}-prometheus"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  volume {
    name = "prometheus-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.obs.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.prometheus.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name         = "prometheus"
      image        = var.image_prometheus
      essential    = true
      portMappings = [{ containerPort = 9090, protocol = "tcp" }]
      mountPoints  = [{ sourceVolume = "prometheus-data", containerPath = "/prometheus" }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.obs["prometheus"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "prometheus"
        }
      }
    }
  ])
}

# Loki
resource "aws_ecs_task_definition" "loki" {
  family                   = "${local.ns}-loki"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  volume {
    name = "loki-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.obs.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.loki.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name         = "loki"
      image        = var.image_loki
      essential    = true
      portMappings = [{ containerPort = 3100, protocol = "tcp" }]
      mountPoints  = [{ sourceVolume = "loki-data", containerPath = "/loki" }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.obs["loki"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "loki"
        }
      }
    }
  ])
}

# Grafana
resource "aws_ecs_task_definition" "grafana" {
  family                   = "${local.ns}-grafana"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  volume {
    name = "grafana-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.obs.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.grafana.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name         = "grafana"
      image        = var.image_grafana
      essential    = true
      portMappings = [{ containerPort = 3000, protocol = "tcp" }]
      mountPoints  = [{ sourceVolume = "grafana-data", containerPath = "/var/lib/grafana" }]
      environment = [
        { name = "GF_SECURITY_ADMIN_USER", value = "admin" },
        { name = "GF_SECURITY_ADMIN_PASSWORD", value = var.grafana_admin_password },
        { name = "GF_SERVER_ROOT_URL", value = "%(protocol)s://%(domain)s${var.grafana_root_url_path}" },
        { name = "GF_SERVER_SERVE_FROM_SUB_PATH", value = "true" },
        { name = "GF_SECURITY_ALLOW_EMBEDDING", value = "true" },
        { name = "GF_SECURITY_COOKIE_SAMESITE", value = "none" },
        # Anonymous OFF; admin pages iframe will need a logged-in Grafana session.
        { name = "GF_AUTH_ANONYMOUS_ENABLED", value = "false" },
        # Allow Grafana provisioning files to interpolate ${VAR}-style refs from env.
        { name = "GF_AUTH_BASIC_ENABLED", value = "true" }
      ]
      secrets = [
        { name = "POSTGRES_HOST", valueFrom = "${var.observability_secret_arn}:POSTGRES_HOST::" },
        { name = "POSTGRES_PORT", valueFrom = "${var.observability_secret_arn}:POSTGRES_PORT::" },
        { name = "POSTGRES_USER", valueFrom = "${var.observability_secret_arn}:POSTGRES_USER::" },
        { name = "POSTGRES_PASSWORD", valueFrom = "${var.observability_secret_arn}:POSTGRES_PASSWORD::" },
        { name = "POSTGRES_DB", valueFrom = "${var.observability_secret_arn}:POSTGRES_DB::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.obs["grafana"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "grafana"
        }
      }
    }
  ])
}

# Postgres exporter
resource "aws_ecs_task_definition" "postgres_exporter" {
  family                   = "${local.ns}-postgres-exporter"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name         = "postgres-exporter"
      image        = var.image_postgres_exporter
      essential    = true
      portMappings = [{ containerPort = 9187, protocol = "tcp" }]
      secrets = [
        { name = "DATA_SOURCE_NAME", valueFrom = "${var.observability_secret_arn}:POSTGRES_DSN::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.obs["postgres-exporter"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "postgres-exporter"
        }
      }
    }
  ])
}

# Redis exporter
resource "aws_ecs_task_definition" "redis_exporter" {
  family                   = "${local.ns}-redis-exporter"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name         = "redis-exporter"
      image        = var.image_redis_exporter
      essential    = true
      portMappings = [{ containerPort = 9121, protocol = "tcp" }]
      secrets = [
        { name = "REDIS_ADDR", valueFrom = "${var.observability_secret_arn}:REDIS_URL::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.obs["redis-exporter"].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis-exporter"
        }
      }
    }
  ])
}

# =============================================================================
# ECS services
# =============================================================================

resource "aws_ecs_service" "prometheus" {
  name            = "${local.ns}-prometheus"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.prometheus.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.obs.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["prometheus"].arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

resource "aws_ecs_service" "loki" {
  name            = "${local.ns}-loki"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.loki.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.obs.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["loki"].arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

resource "aws_ecs_service" "grafana" {
  name                              = "${local.ns}-grafana"
  cluster                           = var.cluster_arn
  task_definition                   = aws_ecs_task_definition.grafana.arn
  desired_count                     = 1
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.obs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.grafana.arn
    container_name   = "grafana"
    container_port   = 3000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["grafana"].arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

resource "aws_ecs_service" "postgres_exporter" {
  name            = "${local.ns}-postgres-exporter"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.postgres_exporter.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.obs.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["postgres-exporter"].arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

resource "aws_ecs_service" "redis_exporter" {
  name            = "${local.ns}-redis-exporter"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.redis_exporter.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.obs.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["redis-exporter"].arn
  }

  lifecycle { ignore_changes = [task_definition] }
}

# =============================================================================
# ALB exposure for Grafana (/grafana/* on existing listener)
# =============================================================================

resource "aws_lb_target_group" "grafana" {
  name        = "${local.ns}-grafana"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    path                = "${var.grafana_root_url_path}/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  deregistration_delay = 30

  tags = { Name = "${local.ns}-grafana" }
}

resource "aws_lb_listener_rule" "grafana" {
  listener_arn = var.alb_listener_arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }

  condition {
    path_pattern {
      values = ["${var.grafana_root_url_path}", "${var.grafana_root_url_path}/*"]
    }
  }
}
