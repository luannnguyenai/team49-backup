# Deploy Folder — Full AWS

Kế hoạch production hiện tại deploy **full AWS**: App Runner cho frontend/backend, RDS PostgreSQL, ElastiCache Redis/Valkey, ECR, Secrets Manager, S3 private bucket, CloudFront, Route 53, và ACM. Data/video lớn đặt trên **AWS S3** và stream qua **CloudFront**. Sau khi mua domain, gắn custom domain cho frontend, backend, CDN.

## Files

- `DEPLOYMENT_PLAN.md`: kế hoạch full AWS theo phase, mỗi phase 1 task, có DoD checklist + files touch + isolation guard + estimate chi phí + CI/CD setup.
- `PRODUCTION_CHECKLIST.md`: checklist trước/trong/sau deploy full AWS.
- `ENVIRONMENT_MATRIX.md`: env variables cho App Runner, RDS, ElastiCache, S3, CloudFront, Secrets Manager, và GitHub Actions.
- `.env.production.example`: template env, không commit secret thật.
- `AWS_CONFIG_GUIDE.md`: hướng dẫn cấu hình full AWS từng dịch vụ.
- `AWS_CICD_GUIDE.md`: hướng dẫn GitHub Actions + AWS OIDC.
- `MANUAL_DEPLOY_STEPS.md`: checklist thao tác tay full AWS.
- `PLATFORM_ANALYSIS.md`: phân tích các lựa chọn triển khai trong AWS.

## Quyết định hiện tại

- 2 App Runner services: `a20-backend`, `a20-frontend`.
- 2 private ECR repositories: `a20-backend`, `a20-frontend`.
- 1 RDS PostgreSQL instance + extension `vector`.
- 1 ElastiCache Redis/Valkey cache.
- 1 AWS S3 private bucket cho course/video assets.
- 1 AWS CloudFront distribution stream asset trực tiếp về browser.
- GitHub Actions deploy production bằng AWS OIDC role, build/push ECR image và update App Runner services.
- Backend không proxy video bytes; chỉ tạo CloudFront URL/metadata.
- Asset delivery config-driven qua `ASSET_STORAGE_PROVIDER=local|s3` để giữ local dev không bị phá.
- Custom domain (`app.<domain>`, `api.<domain>`, `cdn.<domain>`) gắn sau khi mua tên miền.

## Khi nào cần mở rộng plan này

- Cần production lớn, multi-region, SLA cao → cân nhắc ECS Fargate/EKS hoặc kiến trúc multi-region ngoài scope plan v1.
- Cần DRM/protected video pipeline → cần phase mở rộng ngoài scope plan này.
