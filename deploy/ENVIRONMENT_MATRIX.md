# Environment Matrix - AWS-First Simple Managed

Set runtime values in AWS Amplify, App Runner, Secrets Manager, GitHub
Environment values, and local admin shells. Do not commit real `.env` files,
secret values, Terraform state, or Terraform plan artifacts.

## Backend Service `a20-backend` On App Runner

### Core / Database / Cache

| Variable | Example | Store | Note |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASS@RDS_HOST:5432/DB` | Secret reference | Production RDS async URL |
| `REDIS_URL` | `redis://HOST:6379/0` | Secret reference | ElastiCache endpoint; use TLS/auth variant if enabled |
| `DB_ECHO` | `false` | Env | Must stay false in production |
| `DB_POOL_SIZE` | `5` | Env | Start small for App Runner |
| `DB_MAX_OVERFLOW` | `10` | Env | Tune after observing RDS connections |
| `PORT` | `8000` | Env | Backend binds `0.0.0.0:$PORT` |

### Auth / Security

| Variable | Example | Store | Note |
|---|---|---|---|
| `SECRET_KEY` | generated 64 hex chars | Secret reference | Required |
| `ALGORITHM` | `HS256` | Env | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Env | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Env | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | Env | |
| `RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR` | `5` | Env | |
| `EMAIL_FROM` | `noreply@<verified-domain>` | Env/secret | Required if forgot-password email is enabled |
| `FRONTEND_BASE_URL` | `https://<amplify-temp-url>` or `https://app.<domain>` | Env | Reset links and canonical frontend |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | `30` | Env | |
| `CORS_ORIGINS` | `["https://<amplify-temp-url>"]` | Env | JSON array |

### App / LLM Runtime

| Variable | Example | Store | Note |
|---|---|---|---|
| `DEBUG` | `false` | Env | Required |
| `LOG_LEVEL` | `INFO` | Env | |
| `MODEL_PROVIDER` | `openai` / `anthropic` / `gemini` | Env | Select one |
| `DEFAULT_MODEL` | provider model id | Env | Verify availability before setting |
| `FAST_MODEL` | provider model id | Env | |
| `OPENAI_API_KEY` | secret value | Secret reference | Store only if used |
| `ANTHROPIC_API_KEY` | secret value | Secret reference | Store only if used |
| `GEMINI_API_KEY` | secret value | Secret reference | Store only if used |
| `GEMINI_REQUESTS_PER_MINUTE` | `15` | Env | |

### Asset Delivery

| Variable | Example | Store | Note |
|---|---|---|---|
| `ASSET_STORAGE_PROVIDER` | `s3` | Env | `local` only for local development |
| `ASSET_URL_EXPIRE_SECONDS` | `900` | Env | Signed asset URL TTL if enabled |
| `AWS_REGION` | `ap-southeast-1` | Env | Primary AWS region |
| `AWS_S3_BUCKET` | `a20-course-assets-prod` | Env | Private asset bucket |
| `AWS_S3_PREFIX` | `courses` | Env | Stable object prefix |
| `CLOUDFRONT_DOMAIN` | `<id>.cloudfront.net` or `cdn.<domain>` | Env | No scheme |
| `CLOUDFRONT_KEY_PAIR_ID` | key pair id | Secret/env | Only if signed CloudFront URLs are enabled |
| `CLOUDFRONT_PRIVATE_KEY` | private key PEM | Secret reference | Only if signed CloudFront URLs are enabled |

## Frontend App `a20-frontend` On Amplify

| Variable | Example | Store | Note |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend-app-runner-url>` or `https://api.<domain>` | Amplify env | Baked into client build |
| `API_INTERNAL_URL` | same backend URL | Amplify env | Server-side calls if used |
| `NEXT_PUBLIC_GRAFANA_HOST` | optional | Amplify env | Optional |
| `NEXT_PUBLIC_LANGFUSE_HOST` | `https://cloud.langfuse.com` | Amplify env | Optional |
| `NEXT_TELEMETRY_DISABLED` | `1` | Amplify env | |
| `NODE_ENV` | `production` | Amplify env | |

Changing `NEXT_PUBLIC_API_URL` requires a new Amplify build/redeploy.

## App Runner Source Auto Deploy

| Setting | Value |
|---|---|
| Service name | `a20-backend` |
| Repository | this GitHub repository |
| Branch | `main` or selected production branch |
| Source | root `Dockerfile` |
| Port | `8000` or runtime `PORT` |
| Health path | `/health` |
| Auto deploy | enabled |
| VPC connector | required when RDS/ElastiCache are private |
| GitHub connection | authorize outside Terraform, pass ARN into Terraform |

## Amplify GitHub Auto Deploy

| Setting | Value |
|---|---|
| App name | `a20-frontend` |
| Repository | this GitHub repository |
| Branch | `main` or selected production branch |
| App root | `frontend` |
| Install command | `npm ci --legacy-peer-deps` |
| Build command | `npm run build` |
| Auto deploy | enabled |
| GitHub connection | authorize/import preferred; token-in-state requires explicit acceptance |

## RDS PostgreSQL

Run once after provisioning:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Required settings:

- Private subnets only.
- Automated backups enabled.
- Deletion protection enabled for production.
- Storage autoscaling cap recorded.
- Security group allows PostgreSQL only from backend App Runner path.

## ElastiCache Redis OSS / Valkey

Required settings:

- Private subnets only.
- Security group allows cache traffic only from backend App Runner path.
- Endpoint stored as `REDIS_URL` in App Runner secret/env configuration.

## Networking Decision

If App Runner uses a VPC connector to private RDS/ElastiCache and the backend
must call public LLM/email APIs, configure explicit public egress.

Recommended production default:

```text
private RDS/Redis + App Runner VPC connector + NAT Gateway
```

If NAT is deferred, tutor/email production traffic is not considered validated.

## S3 And CloudFront

| Value | Example | Note |
|---|---|---|
| S3 bucket | `a20-course-assets-prod` | Created by Terraform |
| S3 prefix | `courses` | Uploaded outside Terraform |
| CloudFront domain | `<id>.cloudfront.net` | Temporary CDN domain |
| CDN custom domain | `cdn.<domain>` | After Route 53 + ACM setup |

CloudFront must use Origin Access Control so S3 remains private.

## GitHub Actions CI

| Requirement | Value |
|---|---|
| Python | `3.12` |
| Node | `20` |
| Backend checks | Ruff + pytest with Postgres/Redis services |
| Frontend checks | lint + type-check + build + unit tests if available |
| App deploy behavior | none in v1; Amplify/App Runner native auto deploy handles app deploy |

## Terraform Infrastructure CI

Local files that must not be committed:

| File | Purpose |
|---|---|
| `deploy/terraform/live/prod/backend.hcl` | S3 backend config |
| `deploy/terraform/live/prod/terraform.tfvars` | Production variable values |
| `*.tfplan` | Reviewed binary plan files |

GitHub Environment values if Terraform runs in Actions:

| Name | Type | Purpose |
|---|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | secret | OIDC role for Terraform plan/apply |
| `TF_BACKEND_HCL_PROD` | secret or protected variable | Full `backend.hcl` content written at runtime |
| `TFVARS_PROD` | secret or protected variable | Full `terraform.tfvars` content written at runtime |

Recommended local commands:

```bash
cd deploy/terraform/live/prod
terraform init -backend-config=backend.hcl
terraform validate
terraform plan -var-file=terraform.tfvars -out prod.tfplan
terraform apply prod.tfplan
```

## Optional Later App Deploy Variables

Use only after moving backend app deploy to ECR + OIDC:

| Variable | Example |
|---|---|
| `AWS_REGION` | `ap-southeast-1` |
| `AWS_ACCOUNT_ID` | `123456789012` |
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-a20-prod-deploy` |
| `ECR_BACKEND_REPOSITORY` | `a20-backend` |
| `APP_RUNNER_BACKEND_SERVICE_ARN` | App Runner service ARN |
| `PRODUCTION_BACKEND_URL` | `https://api.<domain>` |

## Local/Admin AWS Env

Use local AWS CLI profiles for trusted admin operations:

```bash
aws sts get-caller-identity
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

## After Custom Domain Cutover

Backend:

```text
CORS_ORIGINS=["https://app.<domain>"]
FRONTEND_BASE_URL=https://app.<domain>
CLOUDFRONT_DOMAIN=cdn.<domain>
```

Frontend:

```text
NEXT_PUBLIC_API_URL=https://api.<domain>
API_INTERNAL_URL=https://api.<domain>
```

Redeploy frontend after API URL changes.
