# Environment Matrix — Full AWS

Set runtime values in AWS App Runner, Secrets Manager, GitHub Actions variables, and local admin shells. Do not commit real `.env` files or secret values.

## Backend service `a20-backend` on App Runner

- Private subnets only.
- Automated backups enabled.
- Deletion protection enabled for production.
- Storage autoscaling cap recorded.
- Security group allows PostgreSQL only from backend App Runner path.

| Variable | Value | Note |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASS@HOST:5432/DB` | RDS PostgreSQL URL for SQLAlchemy async |
| `REDIS_URL` | `redis://HOST:6379/0` or TLS/auth variant | ElastiCache Redis OSS/Valkey endpoint |
| `DB_ECHO` | `false` | Must stay false in production |
| `DB_POOL_SIZE` | `5` | Start small for App Runner |
| `DB_MAX_OVERFLOW` | `10` | Tune after observing RDS connections |
| `PORT` | App Runner runtime value or `8000` | Backend must bind `0.0.0.0:$PORT` |

Store `DATABASE_URL` and `REDIS_URL` in Secrets Manager or App Runner secret references.

Required settings:

| Variable | Value | Note |
|---|---|---|
| `SECRET_KEY` | generated 64 hex chars | Store in Secrets Manager |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `5` | |
| `RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR` | `5` | Per IP and normalized email |
| `EMAIL_FROM` | `noreply@<verified-domain>` | Required if forgot-password email is enabled |
| `FRONTEND_BASE_URL` | `https://<frontend-app-runner-url>` or `https://app.<domain>` | Used for reset links |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | `30` | Reset link TTL |
| `CORS_ORIGINS` | `["https://<frontend-app-runner-url>"]` or `["https://app.<domain>"]` | JSON array |

### App / runtime

| Variable | Value | Note |
|---|---|---|
| `DEBUG` | `false` | Required |
| `LOG_LEVEL` | `INFO` | |
| `MODEL_PROVIDER` | `openai` / `anthropic` / `gemini` | |
| `DEFAULT_MODEL` | provider model id | Verify provider availability before setting |
| `FAST_MODEL` | provider model id | |
| `OPENAI_API_KEY` | secret value | Store in Secrets Manager |
| `ANTHROPIC_API_KEY` | secret value | Store in Secrets Manager |
| `GEMINI_API_KEY` | secret value | Store in Secrets Manager |
| `GEMINI_REQUESTS_PER_MINUTE` | `15` | |

### Asset delivery

| Variable | Value | Note |
|---|---|---|
| `ASSET_STORAGE_PROVIDER` | `s3` | `local` only for local development |
| `ASSET_URL_EXPIRE_SECONDS` | `900` | Signed asset URL TTL |
| `AWS_REGION` | `ap-southeast-1` | Primary region |
| `AWS_S3_BUCKET` | `a20-course-assets-prod` | Private bucket |
| `AWS_S3_PREFIX` | `courses` | Prefix containing course assets |
| `CLOUDFRONT_DOMAIN` | `<id>.cloudfront.net` or `cdn.<domain>` | Do not include scheme if app builds URL from domain |
| `CLOUDFRONT_KEY_PAIR_ID` | key pair id | Only if signed CloudFront URLs are enabled |
| `CLOUDFRONT_PRIVATE_KEY` | private key | Store in Secrets Manager only |

## Frontend service `a20-frontend` on App Runner

| Variable | Value | Note |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<backend-app-runner-url>` or `https://api.<domain>` | Baked into frontend build |
| `API_INTERNAL_URL` | same backend URL | For server-side calls if used |
| `NEXT_PUBLIC_GRAFANA_HOST` | optional | |
| `NEXT_PUBLIC_LANGFUSE_HOST` | `https://cloud.langfuse.com` | optional |
| `NEXT_TELEMETRY_DISABLED` | `1` | |
| `NODE_ENV` | `production` | |
| `PORT` | App Runner runtime value or `3000` | Frontend must listen on runtime port |

Changing `NEXT_PUBLIC_API_URL` requires rebuilding and redeploying the frontend image.

## RDS PostgreSQL

Run once after provisioning:

Chosen production default:

```text
private RDS/Redis + App Runner VPC connector + NAT Gateway
```

Required settings:

- Private subnets only.
- Automated backups enabled.
- Storage autoscaling cap recorded.
- Security group allows PostgreSQL only from backend App Runner VPC connector path.

## ElastiCache Redis OSS / Valkey

Required settings:

- Private subnets only.
- Security group allows cache traffic only from backend App Runner VPC connector path.
- Endpoint stored in Secrets Manager or App Runner secret reference.

## S3 and CloudFront

| Variable / value | Example | Note |
|---|---|---|
| S3 bucket | `a20-course-assets-prod` | Block Public Access enabled |
| S3 prefix | `courses` | Upload course assets here |
| CloudFront domain | `<id>.cloudfront.net` | Initial CDN domain |
| CDN custom domain | `cdn.<domain>` | After Route 53 + ACM setup |

CloudFront should use Origin Access Control so S3 remains private.

## GitHub Actions CI/CD

Use GitHub repository or environment variables:

| Variable | Value | Note |
|---|---|---|
| `AWS_REGION` | `ap-southeast-1` | |
| `AWS_ACCOUNT_ID` | account id | |
| `AWS_DEPLOY_ROLE_ARN` | IAM role ARN | OIDC role, not access key |
| `ECR_BACKEND_REPOSITORY` | `a20-backend` | |
| `ECR_FRONTEND_REPOSITORY` | `a20-frontend` | |
| `APP_RUNNER_BACKEND_SERVICE_ARN` | service ARN | |
| `APP_RUNNER_FRONTEND_SERVICE_ARN` | service ARN | |
| `PRODUCTION_BACKEND_URL` | backend default/custom URL | Smoke test target |
| `PRODUCTION_FRONTEND_URL` | frontend default/custom URL | Smoke test target |

No long-lived AWS access keys should be required in GitHub secrets.

## Local/admin AWS env

Use local AWS CLI profiles for provisioning and asset uploads:

```bash
aws sts get-caller-identity
aws s3 sync ./data/courses s3://a20-course-assets-prod/courses --delete
```

Use least-privilege IAM users/roles for admin operations where possible.

## After custom domain cutover

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
