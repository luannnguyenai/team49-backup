resource "aws_ecs_task_definition" "this" {
  family                   = var.service_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = var.environment
      secrets     = var.secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.log_group_name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = var.service_name
        }
      }
    }
  ])
}

resource "aws_ecs_service" "this" {
  name                              = var.service_name
  cluster                           = var.cluster_arn
  task_definition                   = aws_ecs_task_definition.this.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = var.health_check_grace_period_seconds

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = var.service_name
    container_port   = var.container_port
  }

  dynamic "service_registries" {
    for_each = var.service_registry_arn != "" ? [var.service_registry_arn] : []
    content {
      registry_arn   = service_registries.value
      container_name = var.service_registry_container_name != "" ? var.service_registry_container_name : null
    }
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  # Trap B6: don't recreate service on every plan when image is same
  lifecycle {
    ignore_changes = [task_definition]
  }
}
