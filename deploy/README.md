# Deploy Folder — Full AWS

Kế hoạch production hiện tại deploy **full AWS**: App Runner cho frontend/backend, RDS PostgreSQL, ElastiCache Redis/Valkey, ECR, Secrets Manager, S3 private bucket, CloudFront, Route 53, và ACM. Data/video lớn đặt trên **AWS S3** và stream qua **CloudFront**. Sau khi mua domain, gắn custom domain cho frontend, backend, CDN.

## Current Infra Status

Terraform foundation was applied on `2026-05-08` from branch `feat-terraform-aws`.

- Remote state bucket: `a20-terraform-state-prod`
- VPC: `vpc-098d2b446cb653080`
- Private subnets: `subnet-040370baba4649b99`, `subnet-0168765e6c84510c7`
- Asset bucket: `a20-course-assets-prod`
- CloudFront default domain: `d2iilj98tzo5kp.cloudfront.net`
- RDS endpoint: `a20-postgres-prod.cbea2u80yox7.ap-southeast-1.rds.amazonaws.com`
- ElastiCache endpoint: `master.a20-redis-prod.frlokk.apse1.cache.amazonaws.com`

Application services are not created by Terraform yet. Backend/frontend App Runner rollout,
migrations, bootstrap, ECR repositories, and custom domains remain operator steps.

## Source Of Truth

- `DEPLOYMENT_PLAN.md`: kế hoạch full AWS theo phase, mỗi phase 1 task, có DoD checklist + files touch + isolation guard + estimate chi phí + CI/CD setup.
- `PRODUCTION_CHECKLIST.md`: checklist trước/trong/sau deploy full AWS.
- `ENVIRONMENT_MATRIX.md`: env variables cho App Runner, RDS, ElastiCache, S3, CloudFront, Secrets Manager, và GitHub Actions.
- `.env.production.example`: template env, không commit secret thật.
- `AWS_CONFIG_GUIDE.md`: hướng dẫn cấu hình full AWS từng dịch vụ.
- `AWS_CICD_GUIDE.md`: hướng dẫn GitHub Actions + AWS OIDC.
- `MANUAL_DEPLOY_STEPS.md`: checklist thao tác tay full AWS.
- `HOW_TO_FIX.md`: postmortem from the 2026-05-08/09 App Runner + Alembic deployment session.
- `PLATFORM_ANALYSIS.md`: phân tích các lựa chọn triển khai trong AWS.
- `terraform/`: source of truth for AWS foundation infrastructure and Terraform workflow inputs.

1. `DEPLOYMENT_PLAN.md` - authoritative phase plan and gates.
2. `TERRAFORM_PLAN.md` - implementation plan for AWS infrastructure as code.
3. `ENVIRONMENT_MATRIX.md` - runtime variables, secrets, and CI values.
4. `MANUAL_DEPLOY_STEPS.md` - operator runbook for executing the plan.
5. `PRODUCTION_CHECKLIST.md` - final go/no-go checklist.

- 2 App Runner services: `a20-backend`, `a20-frontend`.
- 2 private ECR repositories: `a20-backend`, `a20-frontend`.
- 1 RDS PostgreSQL instance + extension `vector`.
- 1 ElastiCache Redis/Valkey cache.
- 1 AWS S3 private bucket cho course/video assets.
- 1 AWS CloudFront distribution stream asset trực tiếp về browser.
- 1 Terraform remote state S3 bucket: `a20-terraform-state-prod`.
- GitHub Actions deploy production bằng AWS OIDC role, build/push ECR image và update App Runner services.
- GitHub Actions `terraform.yml` validates/plans/applies foundation infra separately from app deploy.
- Backend không proxy video bytes; chỉ tạo CloudFront URL/metadata.
- Asset delivery config-driven qua `ASSET_STORAGE_PROVIDER=local|s3` để giữ local dev không bị phá.
- Custom domain (`app.<domain>`, `api.<domain>`, `cdn.<domain>`) gắn sau khi mua tên miền.

## Khi nào cần mở rộng plan này

- Cần production lớn, multi-region, SLA cao → cân nhắc ECS Fargate/EKS hoặc kiến trúc multi-region ngoài scope plan v1.
- Cần DRM/protected video pipeline → cần phase mở rộng ngoài scope plan này.
