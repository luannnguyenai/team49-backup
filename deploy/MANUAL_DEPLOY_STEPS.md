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
| RDS endpoint | `a20-postgres-prod.cbea2u80yox7.ap-southeast-1.rds.amazonaws.com` |
| ElastiCache endpoint | `master.a20-redis-prod.frlokk.apse1.cache.amazonaws.com` |
| S3 bucket | `a20-course-assets-prod` |
| CloudFront domain | `d2iilj98tzo5kp.cloudfront.net` |
| Final frontend domain | `app.<domain>` |
| Final backend domain | `api.<domain>` |
| Final CDN domain | `cdn.<domain>` |

## 1. Verify AWS CLI identity

```bash
aws sts get-caller-identity
aws configure get region
```

Expected region: `ap-southeast-1`.

## 2. Check Terraform foundation outputs

These resources should already exist from `deploy/terraform/live/prod`:

- VPC: `vpc-098d2b446cb653080`
- Private subnets: `subnet-040370baba4649b99`, `subnet-0168765e6c84510c7`
- RDS instance: `a20-postgres-prod`
- Redis replication group: `a20-redis-prod`
- Asset bucket: `a20-course-assets-prod`
- CloudFront distribution: `d2iilj98tzo5kp.cloudfront.net`

Re-check at any time:

```bash
cd deploy/terraform/live/prod
terraform output
```

Do not recreate these resources manually unless Terraform state is intentionally abandoned.

## 3. Create ECR repositories

```bash
aws ecr create-repository --repository-name a20-backend --region ap-southeast-1
aws ecr create-repository --repository-name a20-frontend --region ap-southeast-1
```

Enable lifecycle policies so only recent SHA-tagged images are retained.

## 4. Build and push backend image

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

## 5. Build and push frontend image

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

## 6. Configure runtime secrets and URLs

Store the values that now come from Terraform:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@a20-postgres-prod.cbea2u80yox7.ap-southeast-1.rds.amazonaws.com:5432/DB
REDIS_URL=redis://master.a20-redis-prod.frlokk.apse1.cache.amazonaws.com:6379/0
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=d2iilj98tzo5kp.cloudfront.net
```

## 7. Verify backend can reach private dependencies

Backend App Runner must attach to the Terraform-created VPC path:

- VPC: `vpc-098d2b446cb653080`
- Private subnets: `subnet-040370baba4649b99`, `subnet-0168765e6c84510c7`
- Security group path created by Terraform for App Runner to reach RDS/Redis

RDS and ElastiCache must remain private.
## 8. Prepare RDS PostgreSQL
RDS is already provisioned by Terraform. Before migrations, create a snapshot:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier a20-postgres-prod \
  --db-snapshot-identifier a20-postgres-prod-before-migration-$(date +%Y%m%d%H%M%S)
```

Enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Store the final async URL:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB
```

## 9. Verify ElastiCache

Store:

```text
REDIS_URL=redis://HOST:6379/0
```

## 10. Upload assets to the existing S3 bucket

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

Record object count and total size:

```bash
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

## 11. Verify CloudFront distribution
CloudFront is already provisioned by Terraform at `d2iilj98tzo5kp.cloudfront.net`.

Verify one representative asset and range request support:

```bash
curl -I -H "Range: bytes=0-1023" "https://d2iilj98tzo5kp.cloudfront.net/courses/<representative-video>.mp4"
```

Expected: `HTTP/1.1 206 Partial Content`

## 12. Store secrets

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

## 13. Create backend App Runner service

Create service from backend ECR image.

Required settings:

- Service name: `a20-backend`
- Port: `8000`
- VPC connector: attached
- Health path: `/health`
- Env/secrets: from `ENVIRONMENT_MATRIX.md`

## 14. Verify Backend App Runner

```bash
curl https://<backend-app-runner-url>/health
```

## 15. Run migrations

Create DB snapshot first, then run migrations from a trusted admin environment or one-off task:

```bash
alembic upgrade head
```

Verify migration head after completion.

## 16. Run bootstrap/import

Run the reviewed production bootstrap wrapper if available:

```bash
bash scripts/aws_bootstrap.sh
```

Verify:

```sql
SELECT COUNT(*) FROM courses;
SELECT COUNT(*) FROM learning_units;
SELECT COUNT(*) FROM lectures;
```

## 17. Verify S3 to DB asset parity

Export DB asset keys and compare with S3 object keys under `courses/`.

Failure condition: any DB asset key points to a missing S3 object.

## 18. Create frontend App Runner service

Create service from frontend ECR image.

Required settings:

- Service name: `a20-frontend`
- Port: `3000`
- Env: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`, `NODE_ENV`, `NEXT_TELEMETRY_DISABLED`

Verify:

```bash
curl https://<frontend-app-runner-url>/api/health
```

## 19. Smoke test temporary AWS domains

- [ ] Backend `/health` returns 200.
- [ ] Frontend health returns 200.
- [ ] Home page loads.
- [ ] Auth flow works.
- [ ] Course catalog loads.
- [ ] Video URL uses CloudFront.
- [ ] Video play and seek work.
- [ ] Browser console has no localhost calls.

## 20. Set up custom domains

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

## 21. Configure CI/CD

Create GitHub Actions variables from `AWS_CICD_GUIDE.md`.

For Terraform workflow, also create:

```text
AWS_TERRAFORM_ROLE_ARN=<role-arn>
TF_BACKEND_HCL_PROD=<full backend.hcl content>
TFVARS_PROD=<full terraform.tfvars content>
```

Create AWS OIDC role and set:

```text
AWS_DEPLOY_ROLE_ARN=<role-arn>
```

Run workflow manually once with `workflow_dispatch`, then rely on `push main` after it is trusted.

## 22. Enable budgets and alarms

- [ ] AWS Budget alerts.
- [ ] CloudFront bytes alarm.
- [ ] App Runner 5xx alarm.
- [ ] RDS CPU/storage alarms.
- [ ] CloudWatch log retention.

## 23. Record rollback data

Record:

- Git commit SHA.
- Backend image digest.
- Frontend image digest.
- RDS snapshot ID before migration.
- CloudFront distribution ID.

Rollback app services by updating App Runner to previous ECR image digest.
