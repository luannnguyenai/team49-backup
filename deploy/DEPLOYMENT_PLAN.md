# Deployment Plan - AWS-First Simple Managed

## Requirement Lock

The production plan optimizes for:

- AWS as the primary production target and learning path.
- Managed AWS services with GitHub-connected auto deploy.
- No manual server SSH work on normal production commits.
- Terraform-managed infrastructure after remote-state bootstrap.
- Private S3 course assets delivered through CloudFront.
- Temporary AWS domains first, custom domains only after smoke tests.
- Isolated changes that preserve local Docker/dev behavior.

## Source Of Truth Rules

1. This file controls phase order and deployment gates.
2. `TERRAFORM_PLAN.md` controls how infrastructure modules are implemented.
3. `ENVIRONMENT_MATRIX.md` controls runtime values and where they are stored.
4. `MANUAL_DEPLOY_STEPS.md` is an execution runbook, not a separate architecture.
5. If docs disagree, update the lower-priority doc to match this file.

## Chosen Feasible V1 Architecture

```text
GitHub
  -> GitHub Actions CI gate
  -> Amplify Hosting auto deploys Next.js frontend
  -> App Runner auto deploys FastAPI backend from repository Dockerfile

Browser
  -> Amplify frontend
  -> App Runner backend API
  -> CloudFront CDN
       -> private S3 bucket with course/video assets

App Runner
  -> VPC connector
       -> private RDS PostgreSQL + pgvector
       -> private ElastiCache Redis/Valkey
  -> NAT Gateway when public LLM/email egress is required
```

Critical rule: large course/video assets must stream directly from CloudFront to
the browser. The backend returns metadata and URLs only.

## Service Choices

| Area | V1 service | Reason |
|---|---|---|
| Frontend | Amplify Hosting | GitHub auto deploy and managed Next.js hosting |
| Backend | App Runner | Managed container runtime and source auto deploy |
| Database | RDS PostgreSQL | Managed backups, standard Postgres, pgvector support |
| Cache | ElastiCache Redis OSS/Valkey | Managed Redis-compatible cache |
| Assets | S3 Standard | Private durable object storage |
| CDN | CloudFront | Range requests, edge delivery, OAC, optional signed URLs |
| Secrets | Secrets Manager + service secret refs | Keeps real values out of git and Terraform variables |
| DNS/TLS | Route 53 + ACM | Native AWS certificates and records |
| Observability | CloudWatch + Budgets | Minimal production operations controls |
| App deploy v1 | Amplify/App Runner native auto deploy | Matches the current codebase with the least app refactor |
| Infra | Terraform | Repeatable reviewed `plan/apply` for foundational AWS resources |

## Locked Defaults

| Item | Value |
|---|---|
| AWS region | `ap-southeast-1` |
| CloudFront certificate region | `us-east-1` |
| Backend App Runner service | `a20-backend` |
| Frontend Amplify app | `a20-frontend` |
| RDS identifier | `a20-postgres-prod` |
| ElastiCache identifier | `a20-redis-prod` |
| S3 asset bucket | `a20-course-assets-prod` |
| S3 asset prefix | `courses` |
| Demo asset scope | `CS224n`, `CS230`, `CS231n` |
| Frontend domain | `app.<domain>` or apex after smoke tests |
| Backend domain | `api.<domain>` after smoke tests |
| CDN domain | `cdn.<domain>` after smoke tests |

## Terraform And Manual Boundaries

Terraform manages for the first production deploy:

- Network, route tables, security groups, NAT when accepted.
- S3 bucket controls and CloudFront.
- RDS and ElastiCache.
- Route 53, ACM, alarms, budgets.
- Secrets Manager containers.

App Runner and Amplify are created through AWS native GitHub authorization first
because that is the most reliable path for this codebase. After both services
work on temporary AWS domains, stable service resources can be imported into
Terraform or recreated by Terraform in a controlled follow-up.

Manual or post-provision steps:

- GitHub OAuth/App Runner connection authorization.
- Amplify repository authorization.
- Token-based Amplify Terraform creation for the first deploy.
- Real secret values.
- Course/video uploads to S3.
- RDS snapshots, Alembic migrations, `CREATE EXTENSION vector`.
- Production bootstrap/import and S3-to-DB parity verification.

## Phase Overview

| Phase | Gate |
|---:|---|
| 0 | Lock deploy variables and budget assumptions |
| 1 | Freeze legacy non-AWS deploy workflow |
| 2 | Bootstrap Terraform state and production root |
| 3 | Align CI as validation gate |
| 4 | Prepare backend for App Runner |
| 5 | Prepare frontend for Amplify |
| 6 | Provision asset infrastructure with Terraform |
| 7 | Upload course assets to S3 |
| 8 | Provision network, database, and cache with Terraform |
| 9 | Store runtime secrets and env values |
| 10 | Create App Runner backend and verify temporary backend URL |
| 11 | Run migrations, bootstrap/import, and asset parity verification |
| 12 | Create Amplify frontend and verify temporary frontend URL |
| 13 | Smoke test temporary AWS domains |
| 14 | Attach custom domains |
| 15 | Add operations controls and rollback records |
| 16 | Optional later: ECR + GitHub OIDC hardening |

## Overall Definition Of Done

The AWS production deployment is done only when the application is running on
AWS managed services, all mandatory gates in this plan have evidence, and
`deploy/PRODUCTION_CHECKLIST.md` is complete for the chosen launch scope.

Done means:

- Legacy Vercel/Railway/Supabase deploys cannot run on `push main`.
- CI is the required merge gate and uses the same Python/Node major versions as
  production.
- Terraform state, foundational infrastructure, plans, and applies are recorded.
- Backend App Runner and frontend Amplify are deployed through the chosen AWS
  GitHub-connected flow.
- RDS, Redis/Valkey, S3, CloudFront, env values, and secrets are configured.
- Alembic migrations and bootstrap/import have run against production RDS.
- Course asset keys in the database match uploaded S3 objects.
- Temporary AWS domains pass smoke tests before any custom domain cutover.
- Final domains, CORS, API URLs, and CDN URLs pass the full smoke test.
- Budget, alarms, logs, rollback records, and deployment IDs are recorded.

## Overall Completion Checklist

- [ ] Every required phase from 0 through 15 has its `Done when` items checked or
  a documented exception approved.
- [ ] `deploy/TERRAFORM_PLAN.md` has been implemented or the remaining Terraform
  ownership boundary is explicitly deferred.
- [ ] `deploy/MANUAL_DEPLOY_STEPS.md` has been followed with command output or
  AWS console evidence recorded.
- [ ] `deploy/PRODUCTION_CHECKLIST.md` has no unchecked mandatory item for the
  selected production launch scope.
- [ ] The deployed commit SHA is recorded and matches the code reviewed for
  launch.
- [ ] A rollback path exists for frontend, backend, database, and assets.
- [ ] First-30-minute production monitoring has no unresolved startup, 5xx,
  database, Redis, asset-delivery, or LLM/email errors.

## Phase 0 - Lock Deploy Variables

**Task:** Record AWS account, region, domain, budget, production branch, service
names, asset scope, LLM provider, and email provider decision.

**May touch:**

- `deploy/DEPLOYMENT_PLAN.md`
- `deploy/ENVIRONMENT_MATRIX.md`
- `deploy/.env.production.example`

**Done when:**

- Region, names, domain layout, and asset scope are recorded.
- Budget threshold and alert recipient are selected.
- NAT decision is explicit: accepted, deferred for smoke tests only, or replaced
  with a documented alternative.
- No cloud runtime resource has been created yet.

## Phase 1 - Freeze Legacy Non-AWS Deploy Workflow

**Task:** Prevent the old Vercel/Railway/Supabase workflow from deploying on
`push main`.

**May touch:**

- `.github/workflows/deploy.yml`
- `deploy/AWS_CICD_GUIDE.md`

**Acceptable outcomes:**

- Disable the `push main` trigger and keep the file as a historical reference.
- Replace it with a manual/no-op reference workflow.
- Delete it after confirming the old stack is not used.

**Done when:**

- `push main` cannot deploy to Vercel/Railway/Supabase.
- GitHub Actions CI still runs before production merges.
- No ECR/OIDC deploy workflow is introduced in this phase.

## Phase 2 - Bootstrap Terraform State And Production Root

**Task:** Create the Terraform management layer described in
`TERRAFORM_PLAN.md`.

**May touch:**

- `.gitignore`
- `deploy/TERRAFORM_PLAN.md`
- `deploy/terraform/**`

**Required behavior:**

- Bootstrap S3 remote state bucket `a20-terraform-state-prod`.
- Use S3 backend with `use_lockfile = true`.
- Create `deploy/terraform/live/prod`.
- Keep real `backend.hcl`, `terraform.tfvars`, state, and plan files out of git.

**Done when:**

- Bootstrap and prod stacks exist.
- `backend.hcl.example` and `terraform.tfvars.example` exist.
- `terraform fmt -check -recursive` and `terraform validate` pass.
- First prod `terraform plan` is reviewed before apply.
- No real secret values are committed.

## Phase 3 - Align CI As Validation Gate

**Task:** Make CI match production runtime requirements before auto deploy.

**May touch:**

- `.github/workflows/ci.yml`
- `.github/workflows/kg-sync.yml` only if Python version alignment is required.

**Done when:**

- CI uses Python 3.12 and Node 20.
- Backend lint/tests run with Postgres and Redis services.
- Frontend lint, type-check, build, and unit tests run where available.
- No production AWS app deploy secrets are added to CI.

## Phase 4 - Prepare Backend For App Runner

**Task:** Verify the backend container can run in App Runner from the repository
Dockerfile.

**May touch:**

- `Dockerfile`
- `.dockerignore`
- `deploy/ENVIRONMENT_MATRIX.md`

**Done when:**

- Dockerfile binds `0.0.0.0:${PORT:-8000}`.
- Local image builds or the local tooling blocker is documented.
- Container starts with and without overridden `PORT`.
- `/health` returns 200.
- `.dockerignore` excludes secrets and large local media.
- No backend business logic changes were made.

## Phase 5 - Prepare Frontend For Amplify

**Task:** Verify the Next.js frontend can build in Amplify Hosting.

**May touch:**

- `frontend/package.json` only if build scripts need alignment.
- `frontend/next.config.mjs` only if Amplify compatibility requires it.
- `frontend/amplify.yml` if autodetection is not enough.
- `deploy/ENVIRONMENT_MATRIX.md`

**Done when:**

- Build command is `npm ci --legacy-peer-deps` then `npm run build`.
- `NEXT_PUBLIC_API_URL` and `API_INTERNAL_URL` strategy is documented.
- Local frontend build succeeds or the blocker is documented.
- No unrelated UI behavior changes were made.

## Phase 6 - Provision Asset Infrastructure With Terraform

**Task:** Create private S3 bucket controls and CloudFront distribution.

**May touch:**

- `deploy/terraform/modules/assets/**`
- `deploy/terraform/live/prod/**`

**Done when:**

- S3 bucket exists with public access block, versioning, and encryption.
- CloudFront distribution uses S3 Origin Access Control.
- Direct public S3 access remains blocked.
- CloudFront default domain is recorded.
- Signed URLs are explicitly enabled or deferred.
- Terraform does not upload course objects.

## Phase 7 - Upload Course Assets To S3

**Task:** Upload selected course assets under the stable prefix.

**May touch:**

- None expected unless a small verification script is added later.

**Done when:**

- Assets exist under `s3://a20-course-assets-prod/courses/`.
- Object count and total size are recorded.
- Representative MP4 object exists.
- Local source files remain intact.

## Phase 8 - Provision Network, Database, And Cache

**Task:** Create the private runtime data plane.

**May touch:**

- `deploy/terraform/modules/network/**`
- `deploy/terraform/modules/database/**`
- `deploy/terraform/modules/cache/**`
- `deploy/terraform/live/prod/**`
- `deploy/ENVIRONMENT_MATRIX.md`

**Required behavior:**

- VPC includes public/private subnets, route tables, and route table associations.
- NAT Gateway is created only when `enable_nat_gateway = true`.
- App Runner security group can reach RDS and Redis.
- RDS and ElastiCache are private.
- RDS master password is AWS-managed or otherwise kept out of git.

**Done when:**

- App Runner VPC connector path is available.
- RDS PostgreSQL exists with backups and deletion protection.
- `CREATE EXTENSION IF NOT EXISTS vector;` has been run and verified.
- ElastiCache Redis OSS/Valkey exists.
- Public egress for LLM/email providers is tested if required.

## Phase 9 - Store Runtime Secrets And Env Values

**Task:** Store production runtime values in AWS-managed locations.

**May touch:**

- `.env.example`
- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

**Done when:**

- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, LLM key, and email values are set
  as service secret references or Secrets Manager values.
- Backend asset settings are set with `ASSET_STORAGE_PROVIDER=s3`.
- Frontend Amplify env includes `NEXT_PUBLIC_API_URL` and `API_INTERNAL_URL`.
- No real secret values are committed.

## Phase 10 - Provision App Runner Backend

**Task:** Create App Runner backend service with source auto deploy using the AWS
native GitHub connection flow.

**May touch:**

- `apprunner.yaml` only if source configuration requires it.
- `deploy/terraform/modules/backend_apprunner/**` only if importing/managing the service after native creation.
- `deploy/terraform/live/prod/**` only if importing/managing the service after native creation.
- `deploy/ENVIRONMENT_MATRIX.md`

**Connection rule:**

- Create/authorize the App Runner GitHub connection outside Terraform.
- Use the repository root `Dockerfile`; the current Dockerfile already binds
  `0.0.0.0:${PORT:-8000}`.
- Do not block the first deploy on Terraform-managed App Runner creation.
- Import or Terraform-manage the service later only after the default-domain
  backend is healthy.

**Done when:**

- Service `a20-backend` exists.
- Auto deploy from production branch is enabled.
- Env/secrets and VPC connector are attached.
- Backend can reach RDS, Redis, and required public providers.
- App Runner default-domain `/health` returns 200.
- Max size/instances are bounded for cost control.

## Phase 11 - Run Migrations, Bootstrap, And Asset Parity

**Task:** Move production data into the AWS data plane.

**May touch:**

- Optional `scripts/aws_bootstrap.sh` if current commands are too easy to misuse.

**Done when:**

- RDS snapshot exists before migration.
- Alembic migrations reach head.
- Bootstrap/import runs exactly once or idempotency behavior is documented.
- Course and learning-unit rows exist.
- DB asset keys match S3 object keys.
- Representative CloudFront MP4 URL plays and seeks in the browser.

## Phase 12 - Create Amplify Frontend

**Task:** Create Amplify app/branch with native GitHub authorization and enable
frontend auto deploy.

**May touch:**

- `frontend/amplify.yml` if needed.
- `deploy/terraform/modules/frontend_amplify/**` only if importing/managing the app after native creation.
- `deploy/terraform/live/prod/**` only if importing/managing the app after native creation.
- `deploy/ENVIRONMENT_MATRIX.md`

**Connection rule:**

- Use Amplify's native GitHub authorization for the first deployment.
- Do not use an Amplify access token for the first deployment path.
- Import or Terraform-manage the app later only after the default-domain
  frontend is healthy.

**Done when:**

- Amplify app `a20-frontend` exists.
- Branch auto deploy is enabled.
- App root is `frontend`.
- Env points to the App Runner temporary backend URL.
- Amplify default domain loads and can call backend health/catalog APIs.

## Phase 13 - Smoke Test Temporary AWS Domains

**Task:** Validate the app before custom domain cutover.

**May touch:** none expected.

**Done when:**

- Amplify default URL loads.
- App Runner default `/health` returns 200.
- Catalog, auth/register/login, learning flow, quiz, and tutor smoke paths pass.
- Video URLs use CloudFront and support seeking.
- Browser console has no `localhost` calls and no mixed content.

## Phase 14 - Attach Custom Domains

**Task:** Attach final frontend, backend, and CDN domains.

**May touch:**

- `deploy/terraform/modules/assets/**`
- `deploy/terraform/modules/backend_apprunner/**`
- `deploy/terraform/modules/frontend_amplify/**`
- `deploy/terraform/live/prod/**`
- `deploy/.env.production.example`
- `deploy/ENVIRONMENT_MATRIX.md`

**Done when:**

- Route 53 hosted zone exists or external DNS delegation is documented.
- `app.<domain>` points to Amplify.
- `api.<domain>` points to App Runner.
- `cdn.<domain>` points to CloudFront.
- ACM certificates are issued and attached.
- Backend CORS/base URL and frontend API URL are updated.
- Frontend is rebuilt after final API URL change.
- Full smoke test passes on final domains.

## Phase 15 - Operations Controls And Rollback Records

**Task:** Add minimal production operations and rollback metadata.

**May touch:**

- `deploy/PRODUCTION_CHECKLIST.md`
- `deploy/terraform/modules/observability/**`
- `deploy/terraform/live/prod/**`
- Optional future `deploy/ROLLBACK.md`

**Done when:**

- AWS Budget and alert recipient are configured.
- CloudFront bytes, App Runner 5xx, RDS CPU/storage, and log-retention controls
  are configured where supported.
- NAT spend review is recorded if NAT is enabled.
- Deployed commit SHA, Amplify deployment ID, App Runner deployment ID, RDS
  snapshot ID, and CloudFront distribution ID are recorded.
- Rollback paths for frontend, backend, DB, and assets are documented.

## Phase 16 - Optional Later ECR/OIDC Hardening

**Task:** Replace native source deploy with a custom deploy workflow only when v1
is stable and the added control is worth the complexity.

**Upgrade when:**

- Immutable Docker image digest rollback is required.
- GitHub Environment approval gates are required for app deploy.
- One workflow must build, tag, update App Runner, wait, and smoke test.

**Done when:**

- OIDC role is least-privilege.
- ECR repository exists.
- Workflow builds SHA-tagged images.
- Workflow updates App Runner and waits for completion.
- Rollback image digests are recorded.

## Current Known Code Touch Points

| Area | File(s) | Reason |
|---|---|---|
| Terraform | `deploy/terraform/**` | AWS infrastructure |
| Backend container | `Dockerfile`, `.dockerignore` | App Runner runtime |
| Frontend build | `frontend/amplify.yml` if needed | Amplify monorepo build |
| Backend config | `src/config.py` | Asset/provider env handling |
| Asset delivery | `src/services/asset_delivery.py` | CloudFront URL generation |
| CI | `.github/workflows/ci.yml` | Production gate |
| Legacy deploy | `.github/workflows/deploy.yml` | Must be frozen before AWS production |
| Bootstrap | `scripts/aws_bootstrap.sh` if needed | Safer production import wrapper |

## Non-Goals For V1

- No ECS, EKS, Kubernetes, multi-region HA, or DRM.
- No custom ECR/OIDC deploy before native AWS auto deploy works.
- No rewrite of course, quiz, auth, planner, recommendation, or UI systems.
- No FastAPI proxying of large course/video assets.
