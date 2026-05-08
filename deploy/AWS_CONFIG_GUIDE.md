# AWS Configuration Guide

Hướng dẫn này dùng cho production full AWS:

- Backend: AWS App Runner từ ECR image `a20-backend`
- Frontend: AWS App Runner từ ECR image `a20-frontend`
- Database: Amazon RDS PostgreSQL + `vector`
- Cache: Amazon ElastiCache Redis OSS hoặc Valkey
- Course/video assets: private Amazon S3 bucket
- Public asset delivery: Amazon CloudFront
- Secrets: AWS Secrets Manager
- DNS/TLS: Route 53 + ACM
- CI/CD: GitHub Actions dùng AWS OIDC role

## 1. Region and names

Use one primary region unless a service explicitly requires another:

```text
AWS_REGION=ap-southeast-1
BACKEND_SERVICE=a20-backend
FRONTEND_SERVICE=a20-frontend
BACKEND_ECR_REPOSITORY=a20-backend
FRONTEND_ECR_REPOSITORY=a20-frontend
RDS_IDENTIFIER=a20-postgres-prod
ELASTICACHE_IDENTIFIER=a20-redis-prod
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
```

CloudFront ACM certificates must be created in `us-east-1`.

## 2. ECR

Create two private repositories:

```bash
aws ecr create-repository --repository-name a20-backend --region ap-southeast-1
aws ecr create-repository --repository-name a20-frontend --region ap-southeast-1
```

Enable image scanning and lifecycle policies so old SHA images do not accumulate indefinitely.

## 3. Network

Create or select a VPC with:

- Private subnets for RDS and ElastiCache.
- Security group for backend App Runner VPC connector.
- Security group for RDS allowing PostgreSQL only from backend security group.
- Security group for ElastiCache allowing Redis only from backend security group.

Keep RDS and ElastiCache private.

## 4. RDS PostgreSQL

Create RDS PostgreSQL in private subnets. Start with Single-AZ for the first production pass unless availability requirements require Multi-AZ.

After the DB is available, enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Use SQLAlchemy async format in app runtime:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB
```

Store DB credentials in Secrets Manager.

## 5. ElastiCache

Create Redis OSS or Valkey in private subnets. Store the endpoint as:

```text
REDIS_URL=redis://HOST:6379/0
```

If auth/TLS is enabled, use the URL shape required by the selected engine settings.

## 6. S3

Create a private bucket:

```bash
aws s3api create-bucket \
  --bucket a20-course-assets-prod \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1
```

Required settings:

- Block Public Access: enabled.
- Versioning: enabled.
- Default encryption: enabled.
- Public bucket policy: not allowed.

Upload assets:

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

## 7. CloudFront

Create a CloudFront distribution:

- Origin: S3 bucket.
- Access: Origin Access Control.
- Allowed methods: `GET`, `HEAD`.
- Viewer protocol policy: redirect HTTP to HTTPS.
- Range requests: supported for MP4 seeking.
- Optional: signed URLs for protected course assets.

If using `cdn.<domain>`, request the ACM certificate in `us-east-1`, then add the alternate domain name to CloudFront.

## 8. Secrets Manager

Store production values in Secrets Manager or App Runner secret references:

```text
DATABASE_URL
REDIS_URL
SECRET_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
EMAIL_FROM
RESEND_API_KEY
CLOUDFRONT_PRIVATE_KEY
```

Do not commit real secret values.

## 9. App Runner backend

Create App Runner service from ECR image:

- Service name: `a20-backend`
- Image: backend ECR repo, commit SHA tag
- Port: `8000` or runtime `PORT`
- VPC connector: attached
- Health path: `/health`

Set backend env:

```text
DATABASE_URL=<Secrets Manager reference>
REDIS_URL=<Secrets Manager reference>
SECRET_KEY=<Secrets Manager reference>
DEBUG=false
LOG_LEVEL=INFO
FRONTEND_BASE_URL=https://<frontend-app-runner-url-or-app-domain>
CORS_ORIGINS=["https://<frontend-app-runner-url-or-app-domain>"]
ASSET_STORAGE_PROVIDER=s3
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=<distribution>.cloudfront.net
```

Verify:

```bash
curl https://<backend-app-runner-url>/health
```

## 10. App Runner frontend

Create App Runner service from ECR image:

- Service name: `a20-frontend`
- Image: frontend ECR repo, commit SHA tag
- Port: `3000` or runtime `PORT`

Set frontend env:

```text
NEXT_PUBLIC_API_URL=https://<backend-app-runner-url-or-api-domain>
API_INTERNAL_URL=https://<backend-app-runner-url-or-api-domain>
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

Changing `NEXT_PUBLIC_API_URL` requires rebuild/redeploy.

## 11. CI/CD

Use GitHub Actions with AWS OIDC:

- Repository variable: `AWS_REGION`
- Repository variable/secret: `AWS_DEPLOY_ROLE_ARN`
- Repository variable: `AWS_ACCOUNT_ID`
- Repository variable: `ECR_BACKEND_REPOSITORY`
- Repository variable: `ECR_FRONTEND_REPOSITORY`
- Repository variable: `APP_RUNNER_BACKEND_SERVICE_ARN`
- Repository variable: `APP_RUNNER_FRONTEND_SERVICE_ARN`
- Repository variable: `PRODUCTION_BACKEND_URL`
- Repository variable: `PRODUCTION_FRONTEND_URL`

The workflow should build images, push SHA tags to ECR, update App Runner services, wait for deployment completion, and run smoke tests.

## 12. Domain cutover

Use Route 53 records:

```text
app.<domain>  -> App Runner frontend custom domain
api.<domain>  -> App Runner backend custom domain
cdn.<domain>  -> CloudFront distribution
```

After domain cutover, update:

```text
FRONTEND_BASE_URL=https://app.<domain>
CORS_ORIGINS=["https://app.<domain>"]
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Redeploy frontend after API URL changes.
