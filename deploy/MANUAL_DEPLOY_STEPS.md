# Manual Deploy Steps — Full AWS

Use this checklist when deploying manually before CI/CD is fully trusted.

## 0. Fill deployment values

| Item | Value |
|---|---|
| AWS account ID | `________________` |
| AWS region | `ap-southeast-1` |
| Backend ECR repo | `a20-backend` |
| Frontend ECR repo | `a20-frontend` |
| Backend App Runner URL | `https://________________` |
| Frontend App Runner URL | `https://________________` |
| RDS endpoint | `________________.rds.amazonaws.com` |
| ElastiCache endpoint | `________________.cache.amazonaws.com` |
| S3 bucket | `a20-course-assets-prod` |
| CloudFront domain | `________________.cloudfront.net` |
| Final frontend domain | `app.<domain>` |
| Final backend domain | `api.<domain>` |
| Final CDN domain | `cdn.<domain>` |

## 1. Verify AWS CLI identity

```bash
aws sts get-caller-identity
aws configure get region
```

Expected region: `ap-southeast-1`.

## 2. Create ECR repositories

```bash
aws ecr create-repository --repository-name a20-backend --region ap-southeast-1
aws ecr create-repository --repository-name a20-frontend --region ap-southeast-1
```

Enable lifecycle policies so only recent SHA-tagged images are retained.

## 3. Build and push backend image

```bash
AWS_ACCOUNT_ID=<account-id>
AWS_REGION=ap-southeast-1
COMMIT_SHA=$(git rev-parse --short=12 HEAD)

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t a20-backend:"$COMMIT_SHA" .
docker tag a20-backend:"$COMMIT_SHA" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-backend:$COMMIT_SHA"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-backend:$COMMIT_SHA"
```

Record the pushed image digest.

## 4. Build and push frontend image

```bash
AWS_ACCOUNT_ID=<account-id>
AWS_REGION=ap-southeast-1
COMMIT_SHA=$(git rev-parse --short=12 HEAD)

docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://<backend-url-or-api-domain> \
  -t a20-frontend:"$COMMIT_SHA" ./frontend

docker tag a20-frontend:"$COMMIT_SHA" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-frontend:$COMMIT_SHA"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/a20-frontend:$COMMIT_SHA"
```

Record the pushed image digest.

## 5. Create private network dependencies

Create or select:

- VPC.
- Private subnets.
- Backend security group path for App Runner VPC connector.
- RDS security group.
- ElastiCache security group.

RDS and ElastiCache must not be public.

## 6. Create RDS PostgreSQL

Create RDS PostgreSQL with:

- Identifier: `a20-postgres-prod`
- Engine: PostgreSQL
- Initial size: `db.t4g.micro` or `db.t4g.small`
- Storage: 20 GB or higher
- Backups: enabled
- Public access: no

Enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Store the final async URL:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB
```

## 7. Create ElastiCache

Create Redis OSS or Valkey in private subnets.

Store:

```text
REDIS_URL=redis://HOST:6379/0
```

## 8. Create S3 bucket and upload assets

```bash
aws s3api create-bucket \
  --bucket a20-course-assets-prod \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1

aws s3api put-public-access-block \
  --bucket a20-course-assets-prod \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-versioning \
  --bucket a20-course-assets-prod \
  --versioning-configuration Status=Enabled

aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

Record object count and total size:

```bash
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

## 9. Create CloudFront distribution

Create a distribution with:

- Origin: S3 bucket.
- Access: Origin Access Control.
- Viewer protocol policy: redirect HTTP to HTTPS.
- Methods: `GET`, `HEAD`.
- Range requests: supported.

Verify one asset through the CloudFront domain.

## 10. Store secrets

Store runtime secrets in Secrets Manager or App Runner secret references:

```text
DATABASE_URL
REDIS_URL
SECRET_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
RESEND_API_KEY
CLOUDFRONT_PRIVATE_KEY
```

## 11. Create backend App Runner service

Create service from backend ECR image.

Required settings:

- Service name: `a20-backend`
- Port: `8000`
- VPC connector: attached
- Health path: `/health`
- Env/secrets: from `ENVIRONMENT_MATRIX.md`

Verify:

```bash
curl https://<backend-app-runner-url>/health
```

## 12. Run migrations

Create DB snapshot first, then run migrations from a trusted admin environment or one-off task:

```bash
alembic upgrade head
```

Verify migration head after completion.

## 13. Run bootstrap/import

Run the reviewed production bootstrap wrapper if available:

```bash
bash scripts/aws_bootstrap.sh
```

Verify:

```sql
SELECT COUNT(*) FROM learning_units;
SELECT COUNT(*) FROM lectures;
```

## 14. Verify S3 to DB asset parity

Export DB asset keys and compare with S3 object keys under `courses/`.

Failure condition: any DB asset key points to a missing S3 object.

## 15. Create frontend App Runner service

Create service from frontend ECR image.

Required settings:

- Service name: `a20-frontend`
- Port: `3000`
- Env: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`, `NODE_ENV`, `NEXT_TELEMETRY_DISABLED`

Verify:

```bash
curl https://<frontend-app-runner-url>/api/health
```

## 16. Smoke test temporary AWS domains

- [ ] Backend `/health` returns 200.
- [ ] Frontend health returns 200.
- [ ] Home page loads.
- [ ] Auth flow works.
- [ ] Course catalog loads.
- [ ] Video URL uses CloudFront.
- [ ] Video play and seek work.
- [ ] Browser console has no localhost calls.

## 17. Set up custom domains

Use Route 53 and ACM:

```text
app.<domain>  -> frontend App Runner custom domain
api.<domain>  -> backend App Runner custom domain
cdn.<domain>  -> CloudFront distribution
```

CloudFront certificate must be in `us-east-1`.

Update backend:

```text
FRONTEND_BASE_URL=https://app.<domain>
CORS_ORIGINS=["https://app.<domain>"]
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Update frontend and rebuild:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

## 18. Configure CI/CD

Create GitHub Actions variables from `AWS_CICD_GUIDE.md`.

Create AWS OIDC role and set:

```text
AWS_DEPLOY_ROLE_ARN=<role-arn>
```

Run workflow manually once with `workflow_dispatch`, then rely on `push main` after it is trusted.

## 19. Enable budgets and alarms

- [ ] AWS Budget alerts.
- [ ] CloudFront bytes alarm.
- [ ] App Runner 5xx alarm.
- [ ] RDS CPU/storage alarms.
- [ ] CloudWatch log retention.

## 20. Record rollback data

Record:

- Git commit SHA.
- Backend image digest.
- Frontend image digest.
- RDS snapshot ID before migration.
- CloudFront distribution ID.

Rollback app services by updating App Runner to previous ECR image digest.
