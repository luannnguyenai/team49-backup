# Production Checklist - AWS-First Simple Managed

Use this while executing `DEPLOYMENT_PLAN.md`. Do not move to the next group
until the current group passes.

## Pre-Deploy Decisions

- [ ] Production branch selected.
- [ ] AWS account and region confirmed: `ap-southeast-1`.
- [ ] Domain layout selected: `app.<domain>`, `api.<domain>`, `cdn.<domain>`.
- [ ] CloudFront ACM region understood: `us-east-1`.
- [ ] LLM provider selected and API key available.
- [ ] Email sender/domain verified if forgot-password is enabled.
- [ ] `SECRET_KEY` generated with a secure random value.
- [ ] AWS Budget threshold and alert recipient selected.
- [ ] NAT decision recorded for App Runner private VPC plus public egress.

## CI And Legacy Workflow

- [ ] Branch protection requires CI before merge.
- [ ] Legacy `.github/workflows/deploy.yml` cannot deploy to Vercel/Railway/Supabase on `push main`.
- [ ] `.github/workflows/ci.yml` uses Python 3.12.
- [ ] CI runs backend lint/tests with Postgres and Redis.
- [ ] CI runs frontend lint/type-check/build and unit tests where available.
- [ ] No long-lived AWS access keys are stored for v1 app deploy.
- [ ] Production app deploy is handled by Amplify/App Runner native auto deploy.

## Terraform Foundation

- [ ] `deploy/TERRAFORM_PLAN.md` reviewed.
- [ ] Terraform state bucket `a20-terraform-state-prod` exists.
- [ ] State bucket has versioning, encryption, and public access block.
- [ ] `deploy/terraform/live/prod/backend.hcl` exists locally and is not committed.
- [ ] `deploy/terraform/live/prod/terraform.tfvars` exists locally and is not committed.
- [ ] `terraform fmt -check -recursive` passes from `deploy/terraform`.
- [ ] `terraform validate` passes from `deploy/terraform/live/prod`.
- [ ] Terraform plan reviewed before every apply.
- [ ] Terraform apply output recorded.
- [ ] No real secret value is present in committed Terraform files or plan artifacts.

## AWS Asset Infrastructure

- [ ] S3 bucket `a20-course-assets-prod` exists.
- [ ] S3 Block Public Access enabled.
- [ ] S3 versioning enabled.
- [ ] S3 default encryption enabled.
- [ ] CloudFront distribution exists with S3 origin.
- [ ] CloudFront uses Origin Access Control.
- [ ] Bucket policy allows CloudFront access only through the distribution.
- [ ] Direct public S3 access is blocked.
- [ ] Course assets uploaded under `s3://a20-course-assets-prod/courses/`.
- [ ] Object count and total size recorded.
- [ ] CloudFront range requests work for MP4 seeking.
- [ ] Signed URL decision recorded.

## Network

- [ ] VPC exists.
- [ ] Public and private subnets exist.
- [ ] Public and private route tables exist.
- [ ] Route table associations exist.
- [ ] NAT Gateway exists if public egress is required.
- [ ] App Runner VPC connector exists.
- [ ] RDS security group allows PostgreSQL only from backend path.
- [ ] ElastiCache security group allows Redis only from backend path.
- [ ] RDS is not publicly accessible.
- [ ] ElastiCache is not publicly accessible.
- [ ] Backend public egress to LLM/email provider works if required.
- [ ] NAT budget impact accepted if NAT is used.

## Database And Cache

- [ ] RDS PostgreSQL instance exists.
- [ ] Automated backups enabled.
- [ ] Deletion protection enabled.
- [ ] Pre-migration snapshot process confirmed.
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;` ran successfully.
- [ ] `SELECT extname FROM pg_extension WHERE extname='vector';` returns `vector`.
- [ ] ElastiCache Redis OSS/Valkey exists.
- [ ] `DATABASE_URL` stored in App Runner secret refs or Secrets Manager.
- [ ] `REDIS_URL` stored in App Runner secret refs or Secrets Manager.

## Backend App Runner

- [ ] GitHub connection authorized and ARN recorded privately.
- [ ] App Runner service `a20-backend` exists.
- [ ] Source points to GitHub repository root `Dockerfile`.
- [ ] Production branch auto deploy is enabled.
- [ ] VPC connector attached if RDS/Redis are private.
- [ ] Health check path `/health` configured.
- [ ] Runtime env/secrets complete:
  - [ ] `DATABASE_URL`
  - [ ] `REDIS_URL`
  - [ ] `SECRET_KEY`
  - [ ] `CORS_ORIGINS`
  - [ ] `FRONTEND_BASE_URL`
  - [ ] selected LLM provider key
  - [ ] `DEBUG=false`
  - [ ] `ASSET_STORAGE_PROVIDER=s3`
  - [ ] `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_S3_PREFIX`, `CLOUDFRONT_DOMAIN`
  - [ ] CloudFront signed URL values if used
- [ ] `curl --fail https://<backend-app-runner-url>/health` returns 200.
- [ ] Backend logs show no secret values and no repeated startup errors.
- [ ] Backend can reach RDS.
- [ ] Backend can reach Redis.
- [ ] Backend can call selected LLM/email provider if enabled.

## Migration And Bootstrap

- [ ] RDS snapshot/backup exists before migration.
- [ ] Alembic migrations ran against RDS.
- [ ] Current migration head verified.
- [ ] Production bootstrap command/wrapper reviewed.
- [ ] Bootstrap/import ran against RDS.
- [ ] Course rows exist.
- [ ] Learning unit rows exist.
- [ ] Admin/demo account policy executed if required.
- [ ] DB asset keys match S3 object keys.

## Frontend Amplify

- [ ] Amplify repository authorization/import path recorded.
- [ ] Amplify app `a20-frontend` exists.
- [ ] Source points to GitHub repository.
- [ ] Production branch auto deploy is enabled.
- [ ] App root is `frontend`.
- [ ] Build settings run `npm ci --legacy-peer-deps` and `npm run build`.
- [ ] `NEXT_PUBLIC_API_URL` points to backend temporary/custom URL.
- [ ] `API_INTERNAL_URL` set if server-side calls need it.
- [ ] `NODE_ENV=production`.
- [ ] `NEXT_TELEMETRY_DISABLED=1`.
- [ ] `curl --fail https://<frontend-amplify-url>/api/health` returns 200.
- [ ] Frontend rebuilt after any API URL change.

## Temporary-Domain Smoke Test

- [ ] Home page loads.
- [ ] Register and login work.
- [ ] Forgot-password works if enabled.
- [ ] Course catalog loads.
- [ ] At least one learning unit loads.
- [ ] Video URL is CloudFront, not local `/data/...`.
- [ ] Video play and seek work.
- [ ] Quiz/session start and submit work.
- [ ] Tutor endpoint responds from selected LLM provider if enabled.
- [ ] Browser console has no `localhost` calls.
- [ ] No mixed-content HTTP.

## Custom Domain

- [ ] Route 53 hosted zone exists or external DNS delegation is documented.
- [ ] `app.<domain>` maps to Amplify frontend.
- [ ] `api.<domain>` maps to App Runner backend.
- [ ] `cdn.<domain>` maps to CloudFront.
- [ ] ACM certs issued and attached.
- [ ] Backend env updated: `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `CLOUDFRONT_DOMAIN`.
- [ ] Frontend env updated: `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`.
- [ ] Frontend rebuilt/redeployed after final API URL change.
- [ ] Full smoke test passes on final domains.

## Cost And Operations

- [ ] AWS Budget alerts enabled.
- [ ] CloudFront bytes alarm enabled.
- [ ] App Runner 5xx alarm enabled.
- [ ] RDS CPU/storage alarms enabled.
- [ ] NAT spend reviewed if NAT is used.
- [ ] CloudWatch log retention set.
- [ ] S3 lifecycle policy reviewed.
- [ ] Deployed commit SHA recorded.
- [ ] Terraform plan/apply timestamp recorded.
- [ ] Amplify deployment ID recorded.
- [ ] App Runner deployment ID recorded.
- [ ] RDS snapshot ID recorded.
- [ ] Rollback path documented.
- [ ] Logs monitored during first 30 minutes.
- [ ] LLM cost monitored after launch.

## Optional Later ECR/OIDC Hardening

- [ ] Need for immutable image rollback confirmed.
- [ ] AWS OIDC deploy role exists and is least-privilege.
- [ ] ECR backend repository exists.
- [ ] Deploy workflow builds SHA-tagged image.
- [ ] Deploy workflow updates App Runner.
- [ ] Deploy workflow waits for deployment completion.
- [ ] Deploy workflow runs smoke tests.
