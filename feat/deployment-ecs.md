# Feature: Deployment ECS

## Architecture liên quan
- [System Architecture](./architecture.md)
- Mục nên xem: `1. Tổng quan hệ thống`, `11. Observability architecture`, `12. Deployment architecture`

## 1. Mục tiêu
Deployment ECS đưa hệ thống lên kiến trúc production trên AWS với frontend/backend tách service, image pipeline rõ ràng, và hạ tầng provision bằng Terraform.

## 2. User/problem this solves
Một repo có frontend Next.js, backend FastAPI, Redis, Postgres, assets, và provider APIs không thể sống lâu trên local Docker. Feature này giải quyết:
- rollout có quy trình;
- tách biệt app release và infra provisioning;
- scale frontend/backend độc lập;
- đưa observability và secrets vào đúng boundary prod.

## 3. System scope
Infra/docs:
- `deploy-ecs/*`
- `deploy-ecs/terraform/*`
- `deploy-ecs/taskdefs/*`
- `cicd/workflows/*`
- `cicd/taskdefs/*`

Supporting config:
- `Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

## 4. Architecture & flow
Theo tài liệu ECS managed V1:

```text
GitHub
  -> GitHub Actions CI
  -> GitHub Actions Deploy
  -> ECR images
  -> ECS services (frontend/backend) on Fargate
  -> ALB ingress
  -> RDS PostgreSQL + ElastiCache
  -> S3 + CloudFront cho assets
  -> Secrets Manager cho runtime secrets
```

Frontend và backend là hai service riêng, cùng chia sẻ cluster nhưng không đóng cùng container runtime.

## 5. Key components
- Terraform modules: `alb`, `ecs_cluster`, `ecs_service`, `database`, `cache`, `assets`, `observability`, `iam_oidc`, `network`, `ecr`.
- Task definitions cho backend/frontend và các tác vụ admin như migrate, seed, env-dump, llm-test.
- GitHub Actions workflows cho CI và deploy.
- CloudFront + S3 cho asset/video delivery.

## 6. Data model / contracts
Feature này không tạo business data model mới, nhưng áp đặt các operational contracts:
- container image revisions là immutable deployment units;
- secrets lấy từ Secrets Manager;
- course videos đi trực tiếp `CloudFront -> Browser`, không proxy qua FastAPI;
- Terraform quản lý infra, không quản lý release state.

## 7. Technical decisions
- Chọn ECS/Fargate thay vì tự quản lý server.
- Tách frontend/backend service để rollout độc lập.
- Dùng ECR + task definition revision thay vì mutable container host.
- Giữ infra as code trong Terraform, deployment orchestration trong GitHub Actions.

## 8. Risks / trade-offs
- ECS/Terraform tăng complexity vận hành so với Docker Compose.
- Cần discipline về env matrix, taskdef versions, và secret rotation.
- LLM/email provider calls phụ thuộc outbound network/NAT.
- Asset delivery split khỏi backend cần được team hiểu rõ, nếu không sẽ dễ vô tình route video qua app server.

## 9. Testing / validation
Tài liệu hữu ích:
- `deploy-ecs/AWS_ARCHITECTURE.md`
- `deploy-ecs/DEPLOYMENT_PLAN.md`
- `deploy-ecs/PRODUCTION_CHECKLIST.md`
- `deploy-ecs/TERRAFORM_PLAN.md`
- `deploy-ecs/ENVIRONMENT_MATRIX.md`

Checks:
- `docker compose` cho local parity
- GitHub Actions CI build/test
- smoke test frontend/backend sau deploy
- Terraform plan review trước apply

## 10. Demo-worthy points
- Rất hợp nếu report cần thêm một tranche về production readiness.
- Cho thấy dự án không dừng ở mức local prototype.
- Có thể kết hợp với observability để thành một chương "deployment and operations".
