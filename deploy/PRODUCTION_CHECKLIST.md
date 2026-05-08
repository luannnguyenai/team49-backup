# Production Checklist — Full AWS

Tick this while executing `DEPLOYMENT_PLAN.md`. Move to the next group only when the previous group passes.

## Pre-deploy

- [ ] Repo is pushed and deploy branch is ready.
- [ ] Backend `Dockerfile` binds `0.0.0.0:${PORT:-8000}`.
- [ ] Frontend `frontend/Dockerfile` listens on runtime `PORT` with fallback `3000`.
- [ ] AWS account has quota for App Runner, ECR, RDS, ElastiCache, S3, CloudFront, Route 53, ACM, Secrets Manager, and CloudWatch.
- [ ] Primary region selected: `ap-southeast-1`.
- [ ] CloudFront certificate region understood: `us-east-1`.
- [ ] Domain layout selected: `app.<domain>`, `api.<domain>`, `cdn.<domain>`.
- [ ] LLM provider selected and API key available.
- [ ] Email provider sender/domain verified if forgot-password is enabled.
- [ ] `SECRET_KEY` generated with a secure random value.
- [ ] AWS Budget thresholds selected.

## CI/CD

- [ ] GitHub Actions deploy role exists and uses AWS OIDC.
- [ ] Deploy role trust policy restricts this repository and production branch/environment.
- [ ] Deploy role has scoped ECR and App Runner permissions.
- [ ] No long-lived AWS access keys are stored in GitHub secrets.
- [ ] `.github/workflows/ci.yml` uses Python 3.12.
- [ ] CI runs backend lint/tests.
- [ ] CI runs frontend lint/type-check/build and unit tests where available.
- [ ] Production deploy workflow builds SHA-tagged ECR images.
- [ ] Production deploy workflow updates App Runner services.
- [ ] Production deploy workflow runs backend/frontend smoke tests.

## ECR

- [ ] ECR repository `a20-backend` exists.
- [ ] ECR repository `a20-frontend` exists.
- [ ] Image scan on push enabled where available.
- [ ] Lifecycle policies configured.
- [ ] Backend image pushed with current commit SHA.
- [ ] Frontend image pushed with current commit SHA.

## Network

- [ ] VPC selected or created.
- [ ] Private subnets selected for RDS and ElastiCache.
- [ ] App Runner VPC connector exists.
- [ ] RDS security group allows PostgreSQL only from backend path.
- [ ] ElastiCache security group allows Redis only from backend path.
- [ ] RDS is not publicly accessible.
- [ ] ElastiCache is not publicly accessible.

## Database and cache

- [ ] RDS PostgreSQL instance exists.
- [ ] Automated backups enabled.
- [ ] Pre-migration snapshot/backup process confirmed.
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;` ran successfully.
- [ ] `SELECT extname FROM pg_extension WHERE extname='vector';` returns `vector`.
- [ ] ElastiCache Redis OSS/Valkey exists.
- [ ] `DATABASE_URL` and `REDIS_URL` stored in Secrets Manager or App Runner secret references.

## AWS asset infra

- [ ] S3 bucket exists in selected region.
- [ ] S3 Block Public Access enabled.
- [ ] S3 versioning enabled.
- [ ] S3 default encryption enabled.
- [ ] `aws s3 sync ./data/courses s3://<bucket>/courses` completed.
- [ ] Object count and total size recorded.
- [ ] CloudFront distribution exists with S3 origin.
- [ ] CloudFront uses Origin Access Control.
- [ ] Direct public S3 access is blocked.
- [ ] CloudFront range requests work for MP4 seeking.
- [ ] Optional signed URL key material stored safely.

## Backend App Runner

- [ ] App Runner service `a20-backend` exists.
- [ ] Backend service uses ECR image tagged with current commit SHA.
- [ ] VPC connector attached.
- [ ] Health check path `/health` configured.
- [ ] Backend env/secrets complete:
  - [ ] `DATABASE_URL`
  - [ ] `REDIS_URL`
  - [ ] `SECRET_KEY`
  - [ ] `CORS_ORIGINS`
  - [ ] `FRONTEND_BASE_URL`
  - [ ] LLM provider key
  - [ ] `DEBUG=false`
  - [ ] `ASSET_STORAGE_PROVIDER=s3`
  - [ ] `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_S3_PREFIX`, `CLOUDFRONT_DOMAIN`
  - [ ] CloudFront signed URL values if used
- [ ] `curl https://<backend-app-runner-url>/health` returns 200.
- [ ] Backend logs show no secret values and no repeated startup errors.

## Database migration and bootstrap

- [ ] DB snapshot/backup exists before migration.
- [ ] Alembic migrations ran against RDS.
- [ ] Current migration head verified.
- [ ] Production bootstrap wrapper reviewed if needed.
- [ ] Bootstrap/import ran against RDS.
- [ ] Course rows exist.
- [ ] Lecture/unit rows exist.
- [ ] Admin/demo account policy executed.
- [ ] DB asset keys match S3 object keys.

## Frontend App Runner

- [ ] App Runner service `a20-frontend` exists.
- [ ] Frontend service uses ECR image tagged with current commit SHA.
- [ ] `NEXT_PUBLIC_API_URL` points to backend default/custom URL.
- [ ] `API_INTERNAL_URL` set if server-side calls need it.
- [ ] `NODE_ENV=production`.
- [ ] `NEXT_TELEMETRY_DISABLED=1`.
- [ ] `curl https://<frontend-app-runner-url>/api/health` returns 200.
- [ ] Frontend rebuilt after any API URL change.

## Smoke test functional

- [ ] Home page loads.
- [ ] Register and login work.
- [ ] Forgot-password flow works if enabled.
- [ ] Course catalog loads.
- [ ] At least one learning unit loads.
- [ ] Video URL is CloudFront, not local `/data/...`.
- [ ] Video play and seek work.
- [ ] Quiz/session start and submit work.
- [ ] Tutor endpoint responds from selected LLM provider.
- [ ] Browser console has no localhost calls.
- [ ] No mixed-content HTTP.

## Custom domain

- [ ] Route 53 hosted zone exists.
- [ ] `app.<domain>` maps to frontend App Runner custom domain.
- [ ] `api.<domain>` maps to backend App Runner custom domain.
- [ ] `cdn.<domain>` maps to CloudFront.
- [ ] ACM certs issued and attached.
- [ ] Backend env updated: `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `CLOUDFRONT_DOMAIN`.
- [ ] Frontend env updated: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`.
- [ ] Frontend rebuilt/redeployed after final API URL change.
- [ ] Full smoke test passes on final domains.

## Cost and operations

- [ ] AWS Budget alerts enabled.
- [ ] CloudFront bytes alarm enabled.
- [ ] App Runner 5xx alarm enabled.
- [ ] RDS CPU/storage alarms enabled.
- [ ] CloudWatch log retention set.
- [ ] ECR lifecycle policy enabled.
- [ ] S3 lifecycle policy reviewed.
- [ ] Deployed commit SHA and image digests recorded.
- [ ] Rollback image digests known.
- [ ] Logs monitored during first 30 minutes.
- [ ] LLM cost monitored after launch.
