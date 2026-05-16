# Environment Matrix — Full AWS ECS

Set runtime values in ECS task definitions, Secrets Manager, GitHub Actions variables, and local admin shells. Do not commit real `.env` files or secret values.

## Backend service `a20-backend` on ECS

Source rule: secrets must be wired via task definition `secrets[]` block bound
to Secrets Manager ARNs. Plain values go in `environment[]`. Never put
`DATABASE_URL`, `REDIS_URL`, or `SECRET_KEY` into `environment[]` (trap B4).

| Variable | Value | Note |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASS@HOST:5432/DB?ssl=require` | **Secret** — Secrets Manager. Production RDS requires SSL; for SQLAlchemy `asyncpg`, use `ssl=require`. If password contains `%`, `alembic/env.py` must escape it (trap A3). |
| `REDIS_URL` | `redis://HOST:6379/0` | **Secret** — Secrets Manager |
| `PORT` | `8000` | Container listens on fixed container port. Must match Dockerfile `EXPOSE` and target group port (trap B3) |
| `DB_ECHO` | `false` | Production default |
| `DB_POOL_SIZE` | `5` | Tune after observing connections |
| `DB_MAX_OVERFLOW` | `10` | Tune after observing load |
| `DEBUG` | `false` | Required |
| `LOG_LEVEL` | `INFO` | |
| `SECRET_KEY` | generated secret | Secrets Manager |
| `FRONTEND_BASE_URL` | `https://app.<domain>` | Used for links/CORS |
| `CORS_ORIGINS` | `["https://app.<domain>"]` | JSON array |

### Asset delivery

| Variable | Value | Note |
|---|---|---|
| `ASSET_STORAGE_PROVIDER` | `s3` | `local` only for local dev |
| `AWS_REGION` | `ap-southeast-1` | Primary region |
| `AWS_S3_BUCKET` | `a20-course-assets-prod` | Private bucket |
| `AWS_S3_PREFIX` | `courses` | Asset prefix |
| `CLOUDFRONT_DOMAIN` | `<id>.cloudfront.net` or `cdn.<domain>` | CDN domain |
| `ASSET_URL_EXPIRE_SECONDS` | `900` | Signed URL TTL if used |

## Frontend service `a20-frontend` on ECS

| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.<domain>` | **Build-time** — baked into bundle. Rebuild + redeploy required if it changes (trap B8) |
| `API_INTERNAL_URL` | ALB URL | Server-side fetch from frontend container |
| `NODE_ENV` | `production` | |
| `PORT` | `3000` | Fixed container port. Must match Dockerfile `EXPOSE` and target group port (trap B3) |
| `HOSTNAME` | `0.0.0.0` | Belt-and-suspenders for Next.js standalone bind. Dockerfile `CMD` already forces it; setting in task def env protects against future Dockerfile drift (trap A2) |
| `NEXT_TELEMETRY_DISABLED` | `1` | |

Changing `NEXT_PUBLIC_API_URL` requires rebuilding and redeploying the
frontend image. Restarting the service alone is not enough.

## GitHub Actions CI/CD

| Variable | Value | Note |
|---|---|---|
| `AWS_REGION` | `ap-southeast-1` | |
| `AWS_ACCOUNT_ID` | account id | |
| `AWS_DEPLOY_ROLE_ARN` | IAM role ARN | OIDC role |
| `ECR_BACKEND_REPOSITORY` | `a20-backend` | |
| `ECR_FRONTEND_REPOSITORY` | `a20-frontend` | |
| `AWS_S3_BUCKET` | `a20-course-assets-prod` | Bucket storing private asset and canonical bundle prefixes |
| `CANONICAL_BUNDLE_PREFIX` | `canonical-bundles` | Private prefix root for versioned canonical bundles |
| `CANONICAL_BUNDLE_VERSION` | e.g. `2026-05-12-cs224n-cs231n-cs230-v1` | Init workflow resolves `s3://$AWS_S3_BUCKET/$CANONICAL_BUNDLE_PREFIX/$CANONICAL_BUNDLE_VERSION/canonical/` |
| `ECS_CLUSTER_NAME` | `a20-prod-cluster` | |
| `ECS_BACKEND_SERVICE_NAME` | `a20-backend` | |
| `ECS_FRONTEND_SERVICE_NAME` | `a20-frontend` | |
| `BACKEND_TASK_FAMILY` | `a20-backend` | |
| `FRONTEND_TASK_FAMILY` | `a20-frontend` | |
| `PRODUCTION_BACKEND_URL` | `https://api.<domain>` or ALB URL | Smoke target |
| `PRODUCTION_FRONTEND_URL` | `https://app.<domain>` or ALB URL | Smoke target |

## Terraform Runtime Inputs

| Variable | Value | Note |
|---|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | IAM role ARN | OIDC role for Terraform workflow |
| `TF_BACKEND_HCL_PROD` | full backend config | runtime-only |
| `TFVARS_PROD` | full production tfvars | runtime-only |

## Local/Admin AWS

Use AWS CLI profiles for provisioning, uploads, migrations, and smoke checks:

```bash
aws sts get-caller-identity
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses
```
