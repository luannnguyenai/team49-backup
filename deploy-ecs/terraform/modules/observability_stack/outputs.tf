output "efs_id" {
  value = aws_efs_file_system.obs.id
}

output "namespace_id" {
  value = aws_service_discovery_private_dns_namespace.obs.id
}

output "obs_security_group_id" {
  value = aws_security_group.obs.id
}

output "grafana_target_group_arn" {
  value = aws_lb_target_group.grafana.arn
}

output "grafana_path" {
  value = var.grafana_root_url_path
}

output "service_arns" {
  value = {
    prometheus        = aws_ecs_service.prometheus.id
    loki              = aws_ecs_service.loki.id
    grafana           = aws_ecs_service.grafana.id
    postgres_exporter = aws_ecs_service.postgres_exporter.id
    redis_exporter    = aws_ecs_service.redis_exporter.id
  }
}
