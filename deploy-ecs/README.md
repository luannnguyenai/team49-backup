# Deploy-ECS Folder — Full AWS ECS

Kế hoạch production trong thư mục này dùng `ECS on Fargate` cho cả frontend và backend, thay cho App Runner. Hạ tầng còn lại giữ hướng full AWS managed: `ALB`, `ECR`, `RDS PostgreSQL`, `ElastiCache Redis/Valkey`, `Secrets Manager`, `S3 private bucket`, `CloudFront`, `Route 53`, `ACM`, `CloudWatch`, và `AWS Budgets`.

Mục tiêu của `deploy-ecs/` là vừa tạo một production path thực tế, vừa giữ cấu trúc đủ rõ để học các khái niệm ECS cốt lõi:

- `ECS cluster`
- `task definition`
- `service`
- `task execution role`
- `task role`
- `ALB`, `listener`, `target group`
- `security group`
- `service autoscaling`
- `ECR image promotion`
- `GitHub Actions + AWS OIDC`

## Chosen V1 Architecture

- `1` ECS cluster: `a20-prod-cluster`
- `2` ECS Fargate services:
  - `a20-frontend`
  - `a20-backend`
- `1` public ALB:
  - `app.<domain>` -> frontend target group
  - `api.<domain>` -> backend target group
- `RDS PostgreSQL` và `ElastiCache` đặt trong private subnets
- `S3 + CloudFront` tiếp tục phục vụ video/assets trực tiếp tới browser

Critical rule: backend không proxy video bytes. Asset/video phải đi `CloudFront -> Browser`.

## Source Of Truth

1. `DESIGN.md`: spec thiết kế cho ECS production v1.
2. `DEPLOYMENT_PLAN.md`: phase order, deployment gates, DoD.
3. `TERRAFORM_PLAN.md`: kế hoạch Terraform và module responsibilities.
4. `ENVIRONMENT_MATRIX.md`: runtime values, secrets, CI/CD variables.
5. `MANUAL_DEPLOY_STEPS.md`: runbook thao tác tuần tự.
6. `PRODUCTION_CHECKLIST.md`: go/no-go checklist.
7. `HOW_TO_FIX.md`: lessons learned + ECS-specific traps. Read before any phase.

## Folder Map

- `terraform/`: Terraform source of truth cho hạ tầng ECS.
- `AWS_ARCHITECTURE.md`: runtime/deploy diagrams và boundary notes.
- `AWS_CICD_GUIDE.md`: build/push ECR, register task definition revision, update ECS service.
- `AWS_CONFIG_GUIDE.md`: hướng dẫn cấu hình AWS services theo compute model ECS.
- `PLATFORM_ANALYSIS.md`: vì sao ECS Fargate được chọn cho lộ trình học và triển khai.

## Non-goals

- Không dùng `EKS` cho v1.
- Không làm `blue/green` phức tạp trong v1.
- Không làm `multi-region`.
- Không đưa `service mesh`, `sidecar observability`, hoặc `private-only ALB` vào v1.
- Không thay đổi business logic ứng dụng ngoài những phần bắt buộc để chạy trên ECS.
