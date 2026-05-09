# ECS Production V1 Design

## Goal

Thiết kế một production path full AWS dùng `ECS on Fargate` để triển khai ứng dụng hiện tại, đồng thời giữ cấu trúc đủ rõ để học và thực hành các thành phần vận hành quan trọng của ECS.

## Scope

- Frontend và backend đều chạy trên `ECS Fargate`
- `ALB` làm entrypoint public cho HTTP/HTTPS
- `ECR` lưu image cho frontend/backend
- `RDS PostgreSQL`, `pgvector`, `ElastiCache`, `Secrets Manager`, `S3`, `CloudFront`, `Route 53`, `ACM`
- `Terraform` là source of truth cho infrastructure
- `GitHub Actions + AWS OIDC` là source of truth cho app deploy

## Runtime Architecture

```text
GitHub
  -> GitHub Actions CI
  -> build Docker images
  -> push ECR
  -> register new ECS task definition revisions
  -> update ECS services

Browser
  -> Route 53
  -> ALB
     -> ECS frontend service
     -> ECS backend service

ECS backend service
  -> RDS PostgreSQL + pgvector
  -> ElastiCache Redis/Valkey
  -> Secrets Manager
  -> NAT Gateway for external egress if needed

Browser
  -> CloudFront
  -> private S3 bucket
```

## Key Decisions

- `1` cluster cho v1 để giảm độ phức tạp học tập
- `2` ECS services tách frontend/backend để giữ boundary rõ
- `Fargate` thay vì `EC2` để tránh phải tự quản container host
- `Rolling deployment` là chiến lược mặc định v1
- `ALB health check` là readiness gate chính cho service rollout
- `CloudWatch logs + budgets + basic alarms` là mức observability tối thiểu

## Operational Boundaries

- Terraform không quản lý object video lớn trong S3
- Terraform không chạy migrations, bootstrap/import, hoặc upload assets
- GitHub Actions không chứa long-lived AWS keys
- Secret thật không nằm trong git, `tfvars`, hoặc image

## Success Criteria

- Có thể build/push/deploy frontend và backend lên ECS bằng commit SHA
- Có thể rollback bằng previous task definition revision hoặc previous image digest
- Backend truy cập được RDS/Redis trong private subnets
- Frontend/backend đi qua ALB và custom domains sau smoke test
- Asset delivery vẫn đi trực tiếp từ CloudFront
