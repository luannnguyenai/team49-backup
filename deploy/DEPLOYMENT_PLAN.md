# Deployment Plan — Full AWS

## Requirement lock

User requirements:

- Deploy **full AWS** for the production path.
- Sau deploy sẽ mua và gắn custom domain.
- Data/course/video assets đặt trong **AWS S3 private bucket** và stream qua **CloudFront**.
- Kế hoạch phải chia phase như cũ.
- **Mỗi phase chỉ làm 1 task**.
- Mỗi phase phải có **DoD checklist**.
- Mỗi phase phải ghi rõ **files sẽ touch**.
- Thay đổi phải **isolated**, tránh ảnh hưởng logic khác.
- Plan phải có **ước tính chi phí AWS theo tháng**.

## Target architecture

```text
Browser
  ├─ AWS App Runner: Next.js frontend
  │    temp:  https://<frontend-service>.<region>.awsapprunner.com
  │    final: https://app.<domain> hoặc https://<domain>
  │
  ├─ AWS App Runner: FastAPI backend
  │    temp:  https://<backend-service>.<region>.awsapprunner.com
  │    final: https://api.<domain>
  │    deps:  RDS PostgreSQL + pgvector, ElastiCache Redis/Valkey
  │
  └─ AWS CloudFront CDN
       final: https://cdn.<domain>
       origin: private S3 bucket
```

Critical rule: video/large assets phải stream trực tiếp `CloudFront -> Browser`. Backend không proxy video bytes từ S3 về user.

## AWS service choices

| Area | AWS service | Decision |
|---|---|---|
| Backend compute | App Runner | Simpler than ECS for first production deploy; deploy from ECR image |
| Frontend compute | App Runner | Keeps full app runtime on AWS |
| Container registry | ECR private repositories | One repo for backend, one repo for frontend |
| Database | RDS PostgreSQL, Single-AZ | Start small with `db.t4g.micro` or `db.t4g.small`; enable `vector` extension |
| Cache/session/rate limit | ElastiCache Redis OSS or Valkey | Start with `cache.t4g.micro` or serverless if ops simplicity wins |
| Assets | S3 Standard | Private bucket, block public access, versioning enabled |
| CDN | CloudFront | S3 origin access control, range requests, optional signed URLs |
| Secrets | Secrets Manager | Store DB URL/passwords, Redis URL, LLM keys, Resend key, CloudFront private key |
| DNS | Route 53 | Hosted zone and records for app/api/cdn |
| TLS | ACM | Public certificates for App Runner custom domains and CloudFront |
| Logs/metrics | CloudWatch | App Runner logs, RDS metrics, CloudFront metrics, budget alarms |
| CI/CD | GitHub Actions + AWS OIDC | CI validates PRs; deploy workflow builds ECR images and updates App Runner without long-lived AWS keys |

## Cost estimate

### Assumptions

- Region: `ap-southeast-1` (Singapore) for app, DB, cache, S3.
- One production environment only.
- Backend: App Runner `1 vCPU / 2 GB`, min 1 provisioned instance.
- Frontend: App Runner `0.5 vCPU / 1 GB`, min 1 provisioned instance.
- Light demo traffic: active CPU about 2 hours/day/service average. Higher traffic increases App Runner active vCPU and CloudFront egress.
- RDS: Single-AZ PostgreSQL, `db.t4g.micro` or `db.t4g.small`, 20 GB gp3/general purpose storage.
- ElastiCache: one small node, no Multi-AZ replica in v1.
- Assets: 15 GB S3 Standard course/video data.
- CloudFront data out examples: 50 GB, 200 GB, and 1 TB/month.
- Does not include LLM/API provider usage, domain registration, taxes, support plan, or one-off migration labor.
- GitHub Actions usage assumed within current GitHub plan/free quota; if private-runner minutes exceed quota, add GitHub billing separately.

### Monthly estimate

| Cost item | Demo/light | Safer small prod | Notes |
|---|---:|---:|---|
| App Runner backend | $15-25 | $35-75 | Depends heavily on active CPU time |
| App Runner frontend | $8-18 | $20-45 | Static-heavy frontend may be cheaper on Amplify/S3, but this plan keeps App Runner |
| RDS PostgreSQL | $18-35 | $35-80 | `db.t4g.micro/small` + 20 GB storage + backup headroom |
| ElastiCache Redis/Valkey | $12-20 | $20-45 | Single small node; serverless can differ |
| S3 Standard 15 GB | <$1 | <$1 | Storage only; requests usually small for this scope |
| CloudFront data out | $5-20 | $20-90 | Main variable; depends on video watch traffic and cache hit |
| ECR private repos | <$2 | <$5 | Depends on image size/retention |
| Secrets Manager | $2-5 | $5-10 | Number of secrets + API calls |
| CloudWatch logs/metrics | $2-10 | $10-30 | Keep retention short at first |
| Route 53 hosted zone | ~$1 | ~$1 | Excludes domain registration |
| ACM public certs | $0 | $0 | Non-exportable public certs for integrated AWS services |
| CI/CD | $0-10 | $0-30 | Usually GitHub Actions minutes/artifact storage; AWS side is mostly ECR/CloudWatch already counted |
| **Estimated total** | **$65-135/month** | **$145-380/month** | Before AWS credits/taxes/support |

### Traffic sensitivity

| Monthly video delivery through CloudFront | Expected added cost |
|---:|---:|
| 50 GB | ~$5-10 |
| 200 GB | ~$15-25 |
| 1 TB | ~$80-100 |

Cost controls:

- Set AWS Budget alerts at `$50`, `$100`, and 80% of remaining AWS credits.
- Add CloudWatch alarm on CloudFront `BytesDownloaded`.
- Keep App Runner max concurrency and max instances bounded until real traffic is known.
- Use S3 lifecycle rules for obsolete assets and ECR lifecycle policies for old images.
- Keep CloudWatch log retention at 7-14 days in v1.

Pricing references to verify before provisioning:

- AWS App Runner Pricing: https://aws.amazon.com/apprunner/pricing/
- Amazon RDS for PostgreSQL Pricing: https://aws.amazon.com/rds/postgresql/pricing/
- Amazon ElastiCache Pricing: https://aws.amazon.com/elasticache/pricing/
- Amazon S3 Pricing: https://aws.amazon.com/s3/pricing/
- Amazon CloudFront Pricing: https://aws.amazon.com/cloudfront/pricing/
- Amazon ECR Pricing: https://aws.amazon.com/ecr/pricing/
- AWS Secrets Manager Pricing: https://aws.amazon.com/secrets-manager/pricing/
- Amazon Route 53 Pricing: https://aws.amazon.com/route53/pricing/
- AWS Certificate Manager Pricing: https://aws.amazon.com/certificate-manager/pricing/
- AWS Pricing Calculator: https://calculator.aws/

## Global rules

1. **One task per phase**: không gom infra + code + data + validation vào cùng phase.
2. **DoD gate**: phase sau chỉ bắt đầu khi DoD phase trước pass.
3. **Isolation**:
   - Không refactor unrelated auth, quiz, planner, recommendation, course ordering.
   - Không đổi DB schema nếu phase không yêu cầu.
   - Không đổi UI/UX nếu phase không yêu cầu.
   - Giữ local dev chạy được.
4. **Asset provider must be config-driven**:
   - `ASSET_STORAGE_PROVIDER=local`: giữ behavior local `/data/...` hiện tại.
   - `ASSET_STORAGE_PROVIDER=s3`: trả CloudFront URL.
5. **No secrets in git**: AWS/DB/Redis/LLM/Resend keys chỉ set trong Secrets Manager, App Runner env, hoặc local `.env` không commit.
6. **CI/CD uses short-lived AWS auth**: GitHub Actions must use OIDC-assumed IAM roles, not committed AWS access keys or long-lived repository secrets.

## Phase overview

| Phase | Single task |
|---:|---|
| 0 | Lock AWS deploy variables |
| 1 | Make backend Docker App Runner-compatible |
| 2 | Make frontend Docker App Runner-compatible |
| 2.1 | Audit and freeze current CI/CD mismatch |
| 2.2 | Create AWS IAM OIDC deploy roles |
| 2.3 | Update CI workflow gates |
| 2.4 | Replace production deploy workflow with AWS App Runner flow |
| 2.5 | Add CI/CD secrets and environment documentation |
| 3 | Create ECR repositories |
| 4 | Build and push backend image to ECR |
| 5 | Build and push frontend image to ECR |
| 6 | Create VPC networking for private dependencies |
| 7 | Create RDS PostgreSQL |
| 8 | Enable pgvector |
| 9 | Create ElastiCache Redis/Valkey |
| 10 | Create private S3 bucket |
| 11 | Upload course assets to S3 |
| 12 | Create CloudFront distribution |
| 12.1 | (Conditional) Set up CloudFront signed URL keys |
| 13 | Store production secrets in Secrets Manager |
| 14 | Add asset delivery config |
| 15 | Add CloudFront asset URL service |
| 16 | Switch course asset URL generation behind config |
| 17 | Create App Runner backend service |
| 18 | Run database migrations |
| 19 | Create production bootstrap wrapper |
| 20 | Run full bootstrap pipeline against RDS |
| 20.1 | Verify S3 to DB asset key parity |
| 21 | Create App Runner frontend service |
| 22 | Smoke test on App Runner temporary domains |
| 23 | Attach frontend/backend custom domains |
| 24 | Attach CDN custom domain |
| 25 | Add budgets and production alarms |
| 26 | Final production-readiness check |
| 27 | Document rollback commands |

---

## Phase 0 — Lock AWS deploy variables

### Task

Chốt biến triển khai trước khi sửa code hoặc tạo cloud resources.

### Files that will be touched

- `deploy/DEPLOYMENT_PLAN.md` only if decisions are recorded.

### Locked decisions

| Hạng mục | Giá trị |
|---|---|
| AWS region | `ap-southeast-1` (Singapore) |
| Backend service name | `a20-backend` |
| Frontend service name | `a20-frontend` |
| Backend ECR repo | `a20-backend` |
| Frontend ECR repo | `a20-frontend` |
| RDS identifier | `a20-postgres-prod` |
| ElastiCache identifier | `a20-redis-prod` |
| S3 bucket name | `a20-course-assets-prod` |
| Demo data | Upload toàn bộ 3 course `CS224n`, `CS230`, `CS231n` (~15GB) lên S3 |
| Custom domain | Mua ở cuối sau khi smoke test pass; Phase 23-24 mới gắn |
| Tạm thời dùng | App Runner default domains và CloudFront default domain |

### DoD checklist

- [ ] AWS region recorded.
- [ ] Service names recorded.
- [ ] Repository/resource names recorded.
- [ ] Domain layout recorded.
- [ ] Demo asset scope recorded.
- [ ] Cost budget thresholds recorded.
- [ ] No code/cloud resource changed before decisions are complete.

### Isolation guard

Planning only. Không sửa Dockerfile, app code, DB, hoặc AWS resources.

---

## Phase 1 — Make backend Docker App Runner-compatible

### Task

Cho backend container listen đúng App Runner runtime port.

### Files that may be touched

- `Dockerfile`
- `.dockerignore` only if build context includes unnecessary large assets.

### Steps

1. Ensure Uvicorn binds `0.0.0.0:${PORT:-8000}`.
2. Preserve app module `src.api.app:app`.
3. Ensure health endpoint stays available.
4. Không sửa API/business logic.

### DoD checklist

- [ ] Backend Dockerfile uses `$PORT` with fallback `8000`.
- [ ] `docker build -t a20-backend .` succeeds, or failure is documented as local tooling issue.
- [ ] Container starts with default port `8000` when `PORT` is not set.
- [ ] Container starts with overridden `PORT`.
- [ ] `/health` returns 200 locally on the chosen port.
- [ ] No backend business logic files changed.

### Isolation guard

Only container startup is in scope. Không chạm auth, DB, course, quiz, LLM, planner, recommendation, asset logic.

---

## Phase 2 — Make frontend Docker App Runner-compatible

### Task

Cho frontend container compatible với App Runner runtime/build.

### Files that may be touched

- `frontend/Dockerfile`
- `frontend/next.config.mjs` only if standalone output is missing/broken.

### Steps

1. Ensure frontend server listens on `${PORT:-3000}`.
2. Preserve `NEXT_PUBLIC_API_URL` as build-time value.
3. Keep Docker build reproducible from `frontend/`.
4. Do not change UI behavior.

### DoD checklist

- [ ] Frontend Dockerfile uses App Runner-compatible port binding.
- [ ] `docker build -t a20-frontend ./frontend` succeeds, or failure is documented.
- [ ] Container starts locally.
- [ ] Home/login route loads locally.
- [ ] No unrelated frontend files changed.

### Isolation guard

Only frontend container startup/build is in scope.

---

## Phase 2.1 — Audit and freeze current CI/CD mismatch

### Task

Ghi nhận rõ workflow hiện tại đang deploy sai target và đóng băng nó trước khi thay bằng full AWS.

### Files that may be touched

- `remaining tasks/cicd/current-state.md`
- `deploy/DEPLOYMENT_PLAN.md` only if CI/CD phase decisions change.

### Current finding

`.github/workflows/deploy.yml` must be aligned to the full AWS production target. The new CI/CD plan should replace any older production deploy path instead of extending it.

### DoD checklist

- [ ] Current deploy workflow providers recorded.
- [ ] Decision recorded: production deploy target is AWS App Runner + ECR + RDS + ElastiCache.
- [ ] Old deploy secrets identified for removal or deprecation.
- [ ] No production deploy workflow is changed before the replacement design is ready.
- [ ] No cloud deployment is triggered in this phase.

### Isolation guard

Documentation/audit only. Do not edit workflow behavior yet.

---

## Phase 2.2 — Create AWS IAM OIDC deploy roles

### Task

Create least-privilege AWS IAM roles for GitHub Actions deployments using OIDC.

### Files that may be touched

- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/.env.production.example`
- Optional future IaC under `deploy/aws/` if requested.

### Required AWS setup

- GitHub OIDC provider in AWS IAM.
- Deploy role trusted only by this repository and protected branches/environments.
- Permissions scoped to:
  - ECR login/push/pull for `a20-backend` and `a20-frontend`.
  - App Runner update/read for `a20-backend` and `a20-frontend`.
  - Secrets Manager read for deploy-time references only if workflow needs it.
  - CloudWatch read for smoke/deploy status if needed.

### DoD checklist

- [ ] IAM OIDC provider exists.
- [ ] GitHub Actions deploy role exists.
- [ ] Trust policy restricts repository, branch, and/or GitHub environment.
- [ ] Role grants ECR permissions only for required repositories.
- [ ] Role grants App Runner permissions only for required services.
- [ ] No long-lived `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` repository secrets are required.
- [ ] Role ARN documented as `AWS_DEPLOY_ROLE_ARN`.

### Isolation guard

IAM setup only. Do not edit workflows or deploy services in this phase.

---

## Phase 2.3 — Update CI workflow gates

### Task

Update CI so PR/main validation matches the project runtime and blocks bad deploys.

### Files that may be touched

- `.github/workflows/ci.yml`
- `.github/workflows/kg-sync.yml` only if Python version alignment is required.
- `remaining tasks/cicd/current-state.md`

### Required CI behavior

- Use Python 3.12 consistently.
- Keep backend lint and tests.
- Keep frontend lint, type-check, and production build.
- Add frontend unit test command if package scripts support it.
- Add `workflow_call` so deploy workflow can reuse CI as a gate.
- Keep branch/PR triggers.

### DoD checklist

- [ ] CI uses Python 3.12.
- [ ] CI still runs backend lint.
- [ ] CI still runs backend tests with Postgres and Redis services.
- [ ] CI still runs frontend lint/type-check/build.
- [ ] Frontend unit tests run if available.
- [ ] `workflow_call` is supported for deploy workflow reuse.
- [ ] CI artifacts remain useful for failures.
- [ ] No deployment step is added to CI.

### Isolation guard

CI validation only. Do not add AWS deploy behavior in this phase.

---

## Phase 2.4 — Replace production deploy workflow with AWS App Runner flow

### Task

Replace the old deploy workflow with an AWS deployment workflow.

### Files that may be touched

- `.github/workflows/deploy.yml`
- Optional helper scripts under `scripts/` only if needed for smoke polling.
- `deploy/ENVIRONMENT_MATRIX.md`

### Required deploy behavior

1. Trigger only on `push` to `main` and optional `workflow_dispatch`.
2. Run CI gate first.
3. Configure AWS credentials with GitHub OIDC role assumption.
4. Build backend image, tag with commit SHA, push to ECR.
5. Update App Runner backend service to the new backend image.
6. Wait for backend operation completion and smoke test `/health`.
7. Build frontend image with the chosen API URL, tag with commit SHA, push to ECR.
8. Update App Runner frontend service to the new frontend image.
9. Wait for frontend operation completion and smoke test the frontend URL.
10. Write image digests, service ARNs, URLs, and smoke results to `GITHUB_STEP_SUMMARY`.

### Required GitHub environment/secrets

- `AWS_REGION`
- `AWS_DEPLOY_ROLE_ARN`
- `AWS_ACCOUNT_ID`
- `ECR_BACKEND_REPOSITORY`
- `ECR_FRONTEND_REPOSITORY`
- `APP_RUNNER_BACKEND_SERVICE_ARN`
- `APP_RUNNER_FRONTEND_SERVICE_ARN`
- `PRODUCTION_BACKEND_URL`
- `PRODUCTION_FRONTEND_URL`

### DoD checklist

- [ ] Old backend deploy step replaced with AWS App Runner update.
- [ ] Old frontend deploy step replaced with AWS App Runner update.
- [ ] Old database secret usage replaced with AWS RDS/Secrets Manager values.
- [ ] Deploy workflow uses OIDC role assumption.
- [ ] Backend image is built, pushed, and deployed by SHA tag.
- [ ] Frontend image is built, pushed, and deployed by SHA tag.
- [ ] App Runner update waits for completion before smoke tests.
- [ ] Failed smoke test fails the workflow.
- [ ] Workflow has `concurrency: deploy-production`.
- [ ] Workflow summary includes deployed commit SHA and image digests.

### Isolation guard

Deploy workflow only. Do not change app code or cloud resources in this phase.

---

## Phase 2.5 — Add CI/CD secrets and environment documentation

### Task

Document all GitHub Actions variables, secrets, and manual controls required for full AWS CI/CD.

### Files that may be touched

- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/README.md`
- `deploy/DEPLOYMENT_PLAN.md`
- Optional new file: `deploy/CICD_AWS_GUIDE.md`

### Documentation requirements

- GitHub repository variables vs secrets.
- GitHub Environment protection rules for `production`.
- Required AWS IAM role ARN and trust-policy expectations.
- Required App Runner service ARNs.
- Required ECR repository names.
- Manual deployment flow with `workflow_dispatch`.
- Rollback by previous ECR image digest.

### DoD checklist

- [ ] All required GitHub Actions variables are listed.
- [ ] All required GitHub Actions secrets are listed, if any.
- [ ] OIDC role setup is documented.
- [ ] Production environment approval requirement is documented.
- [ ] Manual deploy trigger is documented.
- [ ] Rollback input values are documented.
- [ ] No real secret values are committed.

### Isolation guard

Documentation only.

---

## Phase 3 — Create ECR repositories

### Task

Create private ECR repositories for backend and frontend images.

### Files that may be touched

- `deploy/DEPLOYMENT_PLAN.md` only if final repository names change.

### DoD checklist

- [ ] `a20-backend` ECR repo exists.
- [ ] `a20-frontend` ECR repo exists.
- [ ] Image scan on push enabled where available.
- [ ] Lifecycle policy keeps only recent image tags.
- [ ] No app code changed.

### Isolation guard

AWS registry setup only.

---

## Phase 4 — Build and push backend image to ECR

### Task

Build backend container image and push it to ECR.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] AWS CLI authenticated to ECR.
- [ ] Backend image built with a commit SHA tag.
- [ ] Backend image pushed to ECR.
- [ ] Image digest recorded.
- [ ] No secrets baked into image.

### Isolation guard

Image build/push only. Do not deploy App Runner yet.

---

## Phase 5 — Build and push frontend image to ECR

### Task

Build frontend container image and push it to ECR.

### Files that may be touched

- None expected unless Docker build fails due to missing frontend build config.

### DoD checklist

- [ ] Frontend image built with a commit SHA tag.
- [ ] Frontend image pushed to ECR.
- [ ] Image digest recorded.
- [ ] `NEXT_PUBLIC_API_URL` placeholder strategy is documented.
- [ ] No secrets baked into image.

### Isolation guard

Image build/push only. Do not deploy App Runner yet.

---

## Phase 6 — Create VPC networking for private dependencies

### Task

Create the VPC/subnets/security groups required for App Runner VPC connector, RDS, and ElastiCache.

### Files that may be touched

- Optional future IaC file if requested, e.g. `deploy/aws/`.

### DoD checklist

- [ ] VPC selected or created.
- [ ] Private subnets selected for RDS/ElastiCache.
- [ ] App Runner VPC connector can reach private subnets.
- [ ] Security group allows backend to reach RDS.
- [ ] Security group allows backend to reach Redis/Valkey.
- [ ] No public DB/cache endpoint is required.

### Isolation guard

Networking only. Do not create DB/cache/app services in this phase.

---

## Phase 7 — Create RDS PostgreSQL

### Task

Create production PostgreSQL database on RDS.

### Files that may be touched

- `deploy/DEPLOYMENT_PLAN.md` only if DB size/identifier changes.

### DoD checklist

- [ ] RDS PostgreSQL instance exists.
- [ ] Single-AZ or Multi-AZ decision recorded.
- [ ] Storage size and autoscaling cap recorded.
- [ ] Automated backups enabled.
- [ ] DB is private, not publicly accessible.
- [ ] Master credentials stored in Secrets Manager, not git.

### Isolation guard

Database provisioning only. No migrations yet.

---

## Phase 8 — Enable pgvector

### Task

Enable `vector` extension in the RDS database.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] Connected to RDS with admin/migration role.
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;` executed.
- [ ] Extension exists in target database.
- [ ] App schema not changed yet.

### Isolation guard

Extension enablement only.

---

## Phase 9 — Create ElastiCache Redis/Valkey

### Task

Create managed cache for rate limit/session/cache workloads.

### Files that may be touched

- `deploy/DEPLOYMENT_PLAN.md` only if cache engine/size changes.

### DoD checklist

- [ ] Cache cluster/serverless cache exists.
- [ ] Engine choice recorded: Redis OSS or Valkey.
- [ ] Endpoint stored in Secrets Manager or App Runner env source.
- [ ] Security group permits backend access only.
- [ ] No public cache access.

### Isolation guard

Cache provisioning only.

---

## Phase 10 — Create private S3 bucket

### Task

Create private S3 bucket for course/video assets.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] Bucket `a20-course-assets-prod` exists in locked region.
- [ ] Block Public Access enabled.
- [ ] Versioning enabled.
- [ ] Default encryption enabled.
- [ ] Bucket policy does not allow public reads.

### Isolation guard

S3 bucket only. Do not upload app data yet.

---

## Phase 11 — Upload course assets to S3

### Task

Upload course/video assets to S3 under a stable prefix.

### Files that may be touched

- None expected unless upload scripts are created later.

### DoD checklist

- [ ] Assets uploaded under `courses/`.
- [ ] Object count recorded.
- [ ] Total uploaded size recorded.
- [ ] Representative MP4 object exists.
- [ ] Local source files are not deleted.

### Isolation guard

Upload only. Do not change database references yet.

---

## Phase 12 — Create CloudFront distribution

### Task

Create CloudFront distribution for S3-backed course assets.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] CloudFront distribution exists.
- [ ] S3 origin uses Origin Access Control or equivalent private access.
- [ ] Direct public S3 access remains blocked.
- [ ] Range requests work for MP4 seeking.
- [ ] Cache policy recorded.
- [ ] Default CloudFront domain recorded.

### Isolation guard

CDN only. Do not modify app code yet.

---

## Phase 12.1 — Set up CloudFront signed URL keys

### Task

Set up CloudFront signed URL key material if assets must be protected from hotlinking.

### Files that may be touched

- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

### DoD checklist

- [ ] Public key uploaded to CloudFront.
- [ ] Private key stored only in Secrets Manager.
- [ ] Key pair ID recorded as a secret/env value.
- [ ] Test signed URL can access one object.
- [ ] Unsigned URL behavior matches chosen policy.

### Isolation guard

Security key setup only.

---

## Phase 13 — Store production secrets in Secrets Manager

### Task

Store production runtime secrets in AWS Secrets Manager.

### Files that may be touched

- `.env.example` only for placeholder names.
- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

### DoD checklist

- [ ] DB credentials stored.
- [ ] Redis endpoint/auth stored if required.
- [ ] App secret/JWT values stored.
- [ ] Resend/LLM keys stored.
- [ ] CloudFront private key stored if signed URLs are used.
- [ ] No real secret values committed.

### Isolation guard

Secrets setup/docs only. Do not change app runtime yet.

---

## Phase 14 — Add asset delivery config

### Task

Add config values for local vs S3/CloudFront asset delivery.

### Files that may be touched

- `src/config.py`
- `.env.example`
- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

### DoD checklist

- [ ] `ASSET_STORAGE_PROVIDER=local|s3` supported.
- [ ] `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_S3_PREFIX`, `CLOUDFRONT_DOMAIN` documented.
- [ ] Signed URL env values documented if used.
- [ ] Local defaults preserve current `/data/...` behavior.
- [ ] Config fails clearly for incomplete production S3 mode.

### Isolation guard

Config only. Do not change URL generation yet.

---

## Phase 15 — Add CloudFront asset URL service

### Task

Add a service/helper that builds CloudFront asset URLs.

### Files that may be touched

- `src/services/asset_delivery.py` or `src/services/asset_signing.py`
- `tests/services/test_asset_delivery.py` or nearest existing service tests

### DoD checklist

- [ ] Local provider returns current local asset path shape.
- [ ] S3 provider returns CloudFront URL.
- [ ] Signed URL branch works if enabled.
- [ ] Unit tests cover local and S3 modes.
- [ ] No course business logic changed yet.

### Isolation guard

New helper + tests only.

---

## Phase 16 — Switch course asset URL generation behind config

### Task

Use the asset delivery helper where course/lecture/video URLs are returned.

### Files that may be touched

- `src/services/learning_unit_service.py`
- `src/services/content_service.py`
- Nearby tests covering lecture/content payloads

### DoD checklist

- [ ] Local mode returns existing local URLs.
- [ ] S3 mode returns CloudFront URLs.
- [ ] Backend does not proxy video bytes.
- [ ] Existing lecture/catalog tests pass.
- [ ] New/updated tests cover S3 mode.

### Isolation guard

Only asset URL generation is in scope.

---

## Phase 17 — Create App Runner backend service

### Task

Deploy backend image from ECR to App Runner.

### Files that may be touched

- Optional future IaC file if requested.

### DoD checklist

- [ ] App Runner backend service created from backend ECR image.
- [ ] Runtime env/secrets set.
- [ ] VPC connector attached.
- [ ] Backend can reach RDS and ElastiCache.
- [ ] `/health` returns 200 on App Runner default domain.
- [ ] App Runner max instances/concurrency bounded for cost control.

### Isolation guard

Backend deploy only. Do not run migrations/bootstrap yet.

---

## Phase 18 — Run database migrations

### Task

Run application migrations against RDS.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] DB backup/snapshot exists before migration.
- [ ] Migration command executed against RDS.
- [ ] Alembic/current migration state verified.
- [ ] Backend health still passes after migration.
- [ ] No data import run yet.

### Isolation guard

Schema migration only.

---

## Phase 19 — Create production bootstrap wrapper

### Task

Create a reviewed wrapper for production bootstrap/import commands if current scripts require environment setup.

### Files that may be touched

- `scripts/aws_bootstrap.sh` or equivalent new script
- `deploy/DEPLOYMENT_PLAN.md` only if command changes

### DoD checklist

- [ ] Wrapper uses existing import/bootstrap code.
- [ ] Wrapper reads target DB/settings from env.
- [ ] Wrapper is idempotent or documents rerun behavior.
- [ ] Wrapper has no hard-coded secrets.
- [ ] Dry-run/help output works locally if supported.

### Isolation guard

Script wrapper only. Do not run data import in this phase.

---

## Phase 20 — Run full bootstrap pipeline against RDS

### Task

Run the reviewed bootstrap/import pipeline against production RDS.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] Bootstrap command executed once against RDS.
- [ ] Course rows exist.
- [ ] Lecture/unit rows exist.
- [ ] Asset keys are stored as S3 keys, not local absolute paths.
- [ ] Backend API returns catalog data from RDS.

### Isolation guard

Data import only.

---

## Phase 20.1 — Verify S3 to DB asset key parity

### Task

Verify every DB asset key required by the app exists in S3.

### Files that may be touched

- Optional verification script if no existing command can check this.

### DoD checklist

- [ ] DB asset key list exported or queried.
- [ ] S3 object list checked.
- [ ] Missing objects count is zero.
- [ ] Representative video URL works through CloudFront.
- [ ] Verification result recorded.

### Isolation guard

Verification only.

---

## Phase 21 — Create App Runner frontend service

### Task

Deploy frontend image from ECR to App Runner.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] Frontend App Runner service created from frontend ECR image.
- [ ] `NEXT_PUBLIC_API_URL` points to backend default or final API URL.
- [ ] Frontend default domain loads.
- [ ] Frontend can call backend health/catalog.
- [ ] App Runner max instances/concurrency bounded for cost control.

### Isolation guard

Frontend deploy only.

---

## Phase 22 — Smoke test on App Runner temporary domains

### Task

Validate deployed app before custom domain cutover.

### Files that may be touched

- None expected.

### DoD checklist

- [ ] Frontend default URL loads.
- [ ] Backend `/health` returns 200.
- [ ] Catalog page loads courses.
- [ ] Ready course can enter learning flow.
- [ ] Representative lecture video URL is CloudFront.
- [ ] Browser can seek video via CloudFront range requests.
- [ ] Auth/login still works.

### Isolation guard

Validation only.

---

## Phase 23 — Attach frontend/backend custom domains

### Task

Attach custom domains to App Runner frontend and backend.

### Files that may be touched

- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/.env.production.example`

### DoD checklist

- [ ] Route 53 hosted zone exists.
- [ ] ACM/App Runner domain validation complete.
- [ ] `app.<domain>` or apex points to frontend.
- [ ] `api.<domain>` points to backend.
- [ ] Frontend rebuilt/redeployed if API URL changed.
- [ ] HTTPS works for frontend and backend.

### Isolation guard

DNS/domain only.

---

## Phase 24 — Attach CDN custom domain

### Task

Attach `cdn.<domain>` to CloudFront.

### Files that may be touched

- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/.env.production.example`

### DoD checklist

- [ ] ACM certificate for CloudFront created in `us-east-1`.
- [ ] CloudFront alternate domain name configured.
- [ ] Route 53 record points `cdn.<domain>` to CloudFront.
- [ ] Backend `CLOUDFRONT_DOMAIN` updated if needed.
- [ ] Representative asset URL works on CDN custom domain.

### Isolation guard

CDN domain only.

---

## Phase 25 — Add budgets and production alarms

### Task

Add AWS budget alerts and minimal production alarms.

### Files that may be touched

- Optional future IaC file if requested.
- `deploy/PRODUCTION_CHECKLIST.md`

### DoD checklist

- [ ] AWS Budget monthly threshold created.
- [ ] Budget alert recipients configured.
- [ ] CloudFront bytes alarm created.
- [ ] App Runner 5xx alarm created.
- [ ] RDS CPU/storage alarm created.
- [ ] CloudWatch log retention set.

### Isolation guard

Monitoring/cost controls only.

---

## Phase 26 — Final production-readiness check

### Task

Run final checks before calling production ready.

### Files that may be touched

- `deploy/PRODUCTION_CHECKLIST.md`

### DoD checklist

- [ ] No production secret is committed.
- [ ] App URLs and API URLs use final domains.
- [ ] Backend logs show no startup/config errors.
- [ ] RDS backup retention confirmed.
- [ ] S3 public access blocked.
- [ ] CloudFront distribution enabled.
- [ ] Budget alerts enabled.
- [ ] Rollback path documented or ready for Phase 27.

### Isolation guard

Checklist/verification only.

---

## Phase 27 — Document rollback commands

### Task

Document rollback commands and manual rollback steps for app, DB, and assets.

### Files that may be touched

- `deploy/DEPLOYMENT_PLAN.md`
- Optional future file if requested: `deploy/ROLLBACK.md`

### Rollback steps

#### App Runner app rollback

- Backend: update App Runner service to previous ECR image digest.
- Frontend: update App Runner service to previous ECR image digest.

#### Database rollback

Before risky migrations:

```bash
pg_dump "$DATABASE_URL" > backup_before_migration.sql
```

Restore if required:

```bash
psql "$DATABASE_URL" < backup_before_migration.sql
```

For RDS-managed rollback, restore from the pre-migration snapshot into a new instance and repoint `DATABASE_URL` after validation.

#### Asset rollback

If S3 versioning is enabled, restore previous object versions.

If CloudFront cache must be cleared:

```bash
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/courses/*"
```

### DoD checklist

- [ ] Backend rollback path documented.
- [ ] Frontend rollback path documented.
- [ ] DB backup command documented.
- [ ] DB restore command documented.
- [ ] RDS snapshot rollback path documented.
- [ ] S3 versioning status known.
- [ ] CloudFront invalidation command documented.
- [ ] No destructive rollback command executed without explicit confirmation.

### Isolation guard

Documentation only. Do not execute destructive rollback commands unless user explicitly confirms.

---

## Current known future code touch points

These files are not all changed by this plan. They are likely touch points for future implementation phases:

| Area | Likely file(s) | Reason |
|---|---|---|
| Backend App Runner port | `Dockerfile` | Use `$PORT` instead of hard-coded `8000` if required |
| Frontend App Runner runtime | `frontend/Dockerfile` | Ensure App Runner runtime compatibility |
| Config | `src/config.py` | Add AWS/CloudFront asset settings |
| Asset URL builder | `src/services/asset_signing.py` or `src/services/asset_delivery.py` | Generate local or CloudFront asset URLs |
| Course asset URL usage | `src/services/learning_unit_service.py`, `src/services/content_service.py` | Return CloudFront URLs in S3 mode |
| Env docs | `deploy/.env.production.example`, `deploy/ENVIRONMENT_MATRIX.md` | Document full AWS env values |
| CI workflow | `.github/workflows/ci.yml` | Add reusable CI gate, Python 3.12 alignment, frontend test coverage |
| Deploy workflow | `.github/workflows/deploy.yml` | Deploy with AWS OIDC + ECR + App Runner |
| CI/CD docs | `deploy/CICD_AWS_GUIDE.md`, `deploy/ENVIRONMENT_MATRIX.md` | Document GitHub environment variables, OIDC role, manual deploy and rollback |
| Tests | `tests/services/test_asset_delivery.py` or nearby tests | Validate URL generation and provider switch |
| Bootstrap | `scripts/aws_bootstrap.sh` if needed | Wrap production import/bootstrap safely |

## Non-goals

- Keep production hosting on AWS services.
- Do not implement DRM.
- Do not implement multi-region HA in v1.
- Do not build full observability stack beyond CloudWatch alarms/budgets.
- Do not rewrite course, quiz, auth, planner, or recommendation systems.
- Do not proxy large video files through FastAPI.
- Do not introduce Kubernetes/EKS for v1.
