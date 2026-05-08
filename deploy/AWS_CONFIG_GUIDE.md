# AWS Configuration Guide - Simple Managed V1

This guide explains how each AWS service should be configured for the
AWS-first deployment. It does not replace `DEPLOYMENT_PLAN.md`; use it as a
service reference while executing the phase plan.

## 0. Terraform First

After Phase 2, create or update AWS infrastructure with Terraform unless the
deployment plan explicitly calls out a manual step.

```bash
cd deploy/terraform/live/prod
terraform init -backend-config=backend.hcl
terraform validate
terraform plan -var-file=terraform.tfvars -out prod.tfplan
terraform apply prod.tfplan
```

Do not commit:

- `backend.hcl`
- `terraform.tfvars`
- `*.tfplan`
- `*.tfstate`

Manual steps remain valid for:

- GitHub OAuth/App Runner connection authorization.
- Amplify repository authorization or import.
- Entering real secret values.
- Uploading course assets after the S3 bucket exists.
- Running migrations, `CREATE EXTENSION vector`, bootstrap/import, and smoke
  tests.

## 1. Region And Names

```text
AWS_REGION=ap-southeast-1
BACKEND_SERVICE=a20-backend
FRONTEND_APP=a20-frontend
RDS_IDENTIFIER=a20-postgres-prod
ELASTICACHE_IDENTIFIER=a20-redis-prod
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
```

CloudFront custom-domain certificates must be issued in `us-east-1`.

## 2. S3 Asset Bucket

Terraform creates the bucket and security controls.

Required settings:

- Block Public Access enabled.
- Versioning enabled.
- Default encryption enabled.
- No public read policy.
- CloudFront OAC is the only public delivery path.

Upload assets only after Terraform creates the bucket:

```bash
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
aws s3 ls s3://a20-course-assets-prod/courses --recursive --summarize
```

Record object count and total size after upload.

## 3. CloudFront

Terraform creates the distribution.

Required settings:

- Origin: S3 regional domain for the private asset bucket.
- Access: Origin Access Control.
- Methods: `GET`, `HEAD`.
- Viewer protocol policy: redirect HTTP to HTTPS.
- Range requests supported for MP4 seeking.
- Optional signed URLs explicitly enabled or deferred.

If using `cdn.<domain>`, request the CloudFront ACM certificate in `us-east-1`
and add the alternate domain through Terraform.

## 4. Network

Terraform creates or selects:

- VPC.
- Public subnets for NAT Gateway.
- Private subnets for RDS and ElastiCache.
- Public and private route tables plus route table associations.
- App Runner VPC connector security group.
- RDS security group allowing PostgreSQL only from App Runner path.
- ElastiCache security group allowing Redis only from App Runner path.

If App Runner uses a VPC connector for private RDS/Redis and the backend must
call public LLM/email APIs, configure explicit public egress. The recommended
production default is NAT Gateway, with budget alerts because NAT has meaningful
fixed and data-processing cost.

## 5. RDS PostgreSQL

Terraform creates RDS PostgreSQL in private subnets.

Required settings:

- PostgreSQL engine.
- `publicly_accessible = false`.
- Automated backups enabled.
- Deletion protection enabled for production.
- Storage autoscaling cap recorded.
- Master password is AWS-managed or kept out of git.

After provisioning, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

App runtime URL shape:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB
```

Store this as a service secret reference or Secrets Manager value.

## 6. ElastiCache Redis OSS / Valkey

Terraform creates the cache in private subnets.

Runtime URL shape:

```text
REDIS_URL=redis://HOST:6379/0
```

If TLS/auth is enabled, use the URL shape required by the selected engine
configuration.

## 7. Secrets And Runtime Env

Backend service values:

```text
DATABASE_URL
REDIS_URL
SECRET_KEY
OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY
EMAIL_FROM
RESEND_API_KEY or provider-specific email secret
ASSET_STORAGE_PROVIDER=s3
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=a20-course-assets-prod
AWS_S3_PREFIX=courses
CLOUDFRONT_DOMAIN=<distribution>.cloudfront.net or cdn.<domain>
```

Frontend Amplify values:

```text
NEXT_PUBLIC_API_URL=https://<backend-url>
API_INTERNAL_URL=https://<backend-url>
NEXT_TELEMETRY_DISABLED=1
NODE_ENV=production
```

Changing `NEXT_PUBLIC_API_URL` requires a new Amplify build.

## 8. App Runner Backend

App Runner is created by Terraform only after the GitHub connection ARN is
authorized and supplied.

Required settings:

- Service name: `a20-backend`.
- Source: repository root `Dockerfile`.
- Branch: `main` or selected production branch.
- Auto deploy: enabled.
- Port: `8000` or runtime `PORT`.
- VPC connector: attached when RDS/Redis are private.
- Health path: `/health`.

Verify:

```bash
curl --fail https://<backend-app-runner-url>/health
```

## 9. Database Migrations And Bootstrap

Before migrations:

- Confirm an RDS snapshot or backup exists.
- Confirm the admin environment can reach RDS.
- Confirm `DATABASE_URL` targets production RDS, not local or legacy DB.

Run:

```bash
alembic upgrade head
```

Then run the reviewed bootstrap/import command. Prefer a wrapper if added:

```bash
bash scripts/aws_bootstrap.sh
```

Verify catalog data through the backend API before frontend cutover.

## 10. Amplify Frontend

Preferred v1 path:

- Authorize/create or import the Amplify GitHub connection/app.
- Manage stable app/branch/env settings in Terraform where accepted.
- Avoid storing an Amplify access token in Terraform state unless that tradeoff
  is explicitly approved.

Required settings:

- App name: `a20-frontend`.
- Source: GitHub repository.
- Branch: `main` or production branch.
- App root: `frontend`.
- Install command: `npm ci --legacy-peer-deps`.
- Build command: `npm run build`.
- Auto deploy: enabled.

Verify:

```bash
curl --fail https://<frontend-amplify-url>/api/health
```

## 11. Domain Cutover

Attach custom domains only after temporary-domain smoke tests pass.

```text
app.<domain>  -> Amplify frontend
api.<domain>  -> App Runner backend
cdn.<domain>  -> CloudFront distribution
```

After cutover, update backend:

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

## 12. Optional Later ECR/OIDC

Move to a custom deploy pipeline only after native auto deploy is stable:

```text
GitHub Actions -> AWS OIDC -> ECR SHA image -> App Runner service update
```

Use this when immutable image rollback, GitHub Environment deploy approvals, or
single-workflow deploy orchestration become worth the added complexity.
