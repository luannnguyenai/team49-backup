# Deployment Plan — Full AWS ECS

## Requirement Lock

The production plan optimizes for:

- Deploy full AWS with `ECS on Fargate`.
- Sau deploy sẽ mua và gắn custom domain.
- Data/course/video assets đặt trong `AWS S3 private bucket` và stream qua `CloudFront`.
- Kế hoạch phải chia phase như cũ.
- Mỗi phase chỉ làm `1 task`.
- Mỗi phase phải có `DoD checklist`.
- Mỗi phase phải ghi rõ `files sẽ touch`.
- Thay đổi phải `isolated`.
- Plan phải có `ước tính chi phí AWS theo tháng`.
- Plan phải bake-in mọi failure mode đã gặp ở App Runner (xem [`HOW_TO_FIX.md`](HOW_TO_FIX.md)).

## Source Of Truth Rules

1. This file controls phase order and deployment gates.
2. `TERRAFORM_PLAN.md` controls how Terraform modules are designed and adopted.
3. `ENVIRONMENT_MATRIX.md` controls runtime values and where they are stored.
4. `MANUAL_DEPLOY_STEPS.md` is the operator runbook.
5. `HOW_TO_FIX.md` records failure modes already paid for; every phase DoD must respect it.
6. If docs disagree, update the lower-priority doc to match this file.

## Chosen Feasible V1 Architecture

```text
GitHub
  -> GitHub Actions CI gate
  -> GitHub Actions deploy workflow
  -> build backend/frontend images
  -> push ECR
  -> register ECS task definition revisions
  -> update ECS services

Browser
  -> Route 53
  -> Application Load Balancer
     -> ECS frontend service
     -> ECS backend service

Backend ECS service
  -> RDS PostgreSQL + pgvector
  -> ElastiCache Redis/Valkey
  -> Secrets Manager
  -> NAT Gateway (1 AZ) for ECR/Secrets/CloudWatch egress

Browser
  -> CloudFront CDN
  -> private S3 bucket
```

Critical rules:

- Video/large assets phải stream trực tiếp `CloudFront -> Browser`. Backend không proxy video bytes.
- Migrations chạy như **one-off ECS task**, không bao giờ là service start command.
- Smoke test deploy success phải gồm: `/health`, `/api/health`, một DB-backed route, một CloudFront asset.

## AWS Service Choices

| Area | AWS service | Decision |
|---|---|---|
| Backend compute | ECS Fargate service | Main backend runtime |
| Frontend compute | ECS Fargate service | Full containerized runtime on ECS |
| Registry | ECR private repositories | One repo per app |
| Load balancing | ALB | Host-based routing for `app` and `api` |
| Cluster | ECS cluster | Shared cluster for frontend + backend |
| Egress | NAT Gateway (1 AZ) | Required for Fargate ECR/Secrets/Logs pull |
| Database | RDS PostgreSQL Single-AZ | Start small for v1 |
| Cache | ElastiCache Redis OSS or Valkey | Start with one small node |
| Assets | S3 Standard | Private bucket, versioned |
| CDN | CloudFront | OAC, range requests, optional signed URLs |
| Secrets | Secrets Manager | Runtime secret source |
| DNS | Route 53 | `app`, `api`, `cdn` |
| TLS | ACM | ALB and CloudFront certs |
| Logs/metrics | CloudWatch | ECS, ALB, RDS, CloudFront |
| CI/CD | GitHub Actions + AWS OIDC | Build, push, deploy, smoke |

## Cost Estimate

### Assumptions

- Region: `ap-southeast-1`
- One production environment
- Backend task: `1 vCPU / 2 GB`, desired count `1`
- Frontend task: `0.5 vCPU / 1 GB`, desired count `1`
- ALB always on
- 1 NAT Gateway in 1 AZ (single point of failure acceptable for v1)
- RDS `db.t4g.micro` or `db.t4g.small`
- ElastiCache `cache.t4g.micro`
- Assets: `15 GB` in S3
- CloudFront traffic varies by video usage

### Monthly Estimate

| Cost item | Demo/light | Safer small prod | Notes |
|---|---:|---:|---|
| ECS Fargate backend | $18-35 | $40-85 | Depends on task size and uptime |
| ECS Fargate frontend | $10-22 | $20-50 | Depends on task size and uptime |
| ALB | $18-35 | $25-60 | Baseline hourly + LCUs |
| NAT Gateway | $32-40 | $35-55 | Hourly + per-GB processed |
| RDS PostgreSQL | $18-35 | $35-80 | Instance + storage + backup |
| ElastiCache | $12-20 | $20-45 | One small node |
| S3 | <$1 | <$1 | Storage only |
| CloudFront | $5-20 | $20-90 | Main traffic variable |
| ECR | <$2 | <$5 | Image retention dependent |
| Secrets Manager | $2-5 | $5-10 | Secret count dependent |
| CloudWatch | $3-12 | $10-30 | Logs and alarms |
| Route 53 | ~$1 | ~$1 | Excludes domain registration |
| ACM public certs | $0 | $0 | Standard AWS integrated certs |
| **Estimated total** | **$121-228/month** | **$210-511/month** | Before taxes/support |

NAT cost is the biggest jump vs. App Runner. Mitigation if pressure rises:
swap NAT for VPC Interface Endpoints (`ecr.api`, `ecr.dkr`, `logs`,
`secretsmanager`) plus the S3 Gateway Endpoint. Out of scope for v1.

## Global Rules

1. One task per phase.
2. DoD gate: phase sau chỉ bắt đầu khi phase trước pass đầy đủ checklist.
3. Không refactor unrelated app logic.
4. `ASSET_STORAGE_PROVIDER=local|s3` phải giữ local dev không bị phá.
5. No secrets in git, tfvars, image, hoặc task definition `environment`.
6. CI/CD uses AWS OIDC, not long-lived access keys.
7. Rollback path phải có trước khi gọi production ready.
8. Mỗi failure mode đã ghi trong `HOW_TO_FIX.md` phải có ít nhất 1 DoD item ngăn nó tái diễn.

## Phase List

| Phase | Single task | Failure mode it prevents |
|---:|---|---|
| 0 | Lock ECS deploy variables | — |
| 1 | Make backend Docker ECS-compatible | A1, B3 |
| 2 | Make frontend Docker ECS-compatible | A2, B3, B8 |
| 3 | Audit current CI/CD and replace App Runner assumptions | — |
| 4 | Create AWS IAM OIDC deploy roles | B5 |
| 5 | Create ECR repositories | — |
| 6 | Build and push backend image to ECR | A1, B3 |
| 7 | Build and push frontend image to ECR | A2, B8 |
| 8 | Create VPC, subnets, routes, NAT, security groups | B1 |
| 9 | Create ALB, listeners, target groups | B2, B3 |
| 10 | Create ECS cluster and CloudWatch log groups | B7 |
| 11 | Create RDS PostgreSQL with deletion_protection | A6 |
| 12 | Enable pgvector | — |
| 13 | Create ElastiCache Redis/Valkey | — |
| 14 | Create private S3 bucket | — |
| 15 | Upload course assets to S3 | — |
| 16 | Create CloudFront distribution with OAC | — |
| 17 | Store production secrets in Secrets Manager | B4 |
| 18 | Add asset delivery config | — |
| 19 | Create backend task definition and ECS service | B2, B3, B4, B5, B7 |
| 20 | Run database migrations as one-off ECS task | A3, A4 |
| 21 | Run bootstrap/import against RDS | A5 |
| 22 | Create frontend task definition and ECS service | A2, B2, B8 |
| 23 | Add ECS autoscaling and CloudWatch alarms | — |
| 24 | Smoke test on ALB DNS (full pack) | A5, B6 |
| 25 | Attach custom domains and rebuild frontend | B8 |
| 26 | Add budgets and production alarms | — |
| 27 | Document rollback and teardown commands | A6 |

Failure-mode codes refer to sections in [`HOW_TO_FIX.md`](HOW_TO_FIX.md).

---

## Phase 0 — Lock ECS deploy variables

### Task

Chốt naming, region, domain layout, sizing, và budget thresholds.

### Files that will be touched

- `deploy-ecs/DEPLOYMENT_PLAN.md` only if decisions change

### Locked decisions

| Hạng mục | Giá trị |
|---|---|
| AWS region | `ap-southeast-1` |
| ECS cluster | `a20-prod-cluster` |
| Backend service | `a20-backend` |
| Frontend service | `a20-frontend` |
| Backend ECR repo | `a20-backend` |
| Frontend ECR repo | `a20-frontend` |
| ALB name | `a20-public-alb` |
| Asset bucket | `a20-course-assets-prod` |
| Backend container port | `8000` |
| Frontend container port | `3000` |
| Backend log group | `/ecs/a20-backend` |
| Frontend log group | `/ecs/a20-frontend` |
| Migration task family | `a20-backend-migrate` |
| Domain layout | `app.<domain>`, `api.<domain>`, `cdn.<domain>` |

### DoD checklist

- [ ] Region recorded
- [ ] Names recorded
- [ ] Container ports recorded
- [ ] Log groups named
- [ ] Migration task family named
- [ ] Domain layout recorded
- [ ] Budget thresholds recorded
- [ ] No cloud resource changed yet

### Isolation guard

Planning only.

---

## Phase 1 — Make backend Docker ECS-compatible

### Task

Confirm backend image starts without DVC noise, listens on `0.0.0.0:8000`, and
exposes `/health`.

### Files that will be touched

- `.dockerignore` (verify only)
- `Dockerfile` (verify only)
- `alembic/env.py` (verify `%` escape still in place)

### DoD checklist

- [ ] `.dockerignore` excludes `.dvc/`, `.git/`, `node_modules/`, `frontend/`
- [ ] `docker build -t a20-backend:local .` succeeds locally with no DVC content in context
- [ ] Container `EXPOSE 8000` present
- [ ] `docker run -p 8000:8000 a20-backend:local` returns `200` on `GET /health`
- [ ] `alembic/env.py` still has `settings.database_url.replace("%", "%%")`
- [ ] No app logic changed beyond what is required

### Isolation guard

Code-only verification. No AWS resources.

---

## Phase 2 — Make frontend Docker ECS-compatible

### Task

Confirm frontend image binds `0.0.0.0:3000` regardless of any platform-injected
`HOSTNAME`, and bakes correct `NEXT_PUBLIC_*` build args.

### Files that will be touched

- `frontend/Dockerfile` (verify only)

### DoD checklist

- [ ] `CMD` forces `HOSTNAME=0.0.0.0` at runtime (not just `ENV`)
- [ ] `EXPOSE 3000` present
- [ ] Build args `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL` exist with non-localhost prod defaults overridable at build time
- [ ] Local container `GET /api/health` returns `200`
- [ ] Local container `GET /` returns `200`
- [ ] `HEALTHCHECK` line still resolves `${PORT:-3000}`

### Isolation guard

Code-only verification.

---

## Phase 3 — Audit current CI/CD and replace App Runner assumptions

### Task

Strip App Runner-specific steps from `.github/workflows/` and replace with ECS
deploy stubs that reference task definition rendering and `aws ecs update-service`.

### Files that will be touched

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-prod.yml` (rename or replace App Runner deploy)
- `deploy-ecs/AWS_CICD_GUIDE.md`

### DoD checklist

- [ ] No `apprunner` API calls remain in workflows
- [ ] OIDC role assumed before any AWS call
- [ ] Build uses immutable SHA tags (`<repo>:<sha>`), never `latest`
- [ ] Workflow renders task definition JSON from a committed template
- [ ] Workflow `aws ecs update-service --force-new-deployment` flow documented
- [ ] `aws ecs wait services-stable` followed by HTTP smoke (not as the only gate)
- [ ] `concurrency: deploy-production` group present

### Isolation guard

CI changes only. No image build, no AWS apply yet.

---

## Phase 4 — Create AWS IAM OIDC deploy roles

### Task

Create two IAM roles:

- `a20-gha-deploy`: build/push ECR, register task definition, update service
- `a20-gha-terraform`: plan/apply infra (separate trust policy)

Plus the **task execution role** and **task role** templates referenced later.

### Files that will be touched

- `deploy-ecs/terraform/modules/iam_oidc/`
- `deploy-ecs/terraform/live/prod/main.tf`

### DoD checklist

- [ ] OIDC provider for `token.actions.githubusercontent.com` exists
- [ ] Deploy role trust restricts `repo:<org>/<repo>:ref:refs/heads/main` and `environment:production`
- [ ] Deploy role policy: ECR push, ECS register/update, IAM passRole limited to task roles
- [ ] Terraform role trust scoped same way
- [ ] Task execution role separate from task role (B5)
- [ ] Task execution role has `AmazonECSTaskExecutionRolePolicy` + scoped `secretsmanager:GetSecretValue`
- [ ] Task role policy is least-privilege per service (e.g. backend gets `s3:GetObject` on assets prefix only)
- [ ] No long-lived AWS keys in repo

### Isolation guard

IAM only.

---

## Phase 5 — Create ECR repositories

### Files that will be touched

- `deploy-ecs/terraform/modules/ecr/`
- `deploy-ecs/terraform/live/prod/main.tf`

### DoD checklist

- [ ] `a20-backend` repo exists, image scanning on push enabled
- [ ] `a20-frontend` repo exists, scanning on push enabled
- [ ] Lifecycle policy keeps last 20 images
- [ ] Tag immutability enabled to prevent SHA tag overwrite

### Isolation guard

Registry only.

---

## Phase 6 — Build and push backend image to ECR

### DoD checklist

- [ ] Pre-flight from `HOW_TO_FIX.md` section C "Before Phase 6" all green
- [ ] Image tagged `<account>.dkr.ecr.<region>.amazonaws.com/a20-backend:<sha>`
- [ ] Image digest recorded in step summary
- [ ] No `latest` tag pushed
- [ ] `docker run` against pulled image returns `200` on `/health`

### Isolation guard

ECR write only.

---

## Phase 7 — Build and push frontend image to ECR

### DoD checklist

- [ ] Pre-flight from `HOW_TO_FIX.md` section C "Before Phase 7" all green
- [ ] Build args use production `NEXT_PUBLIC_API_URL` (placeholder if domain not yet bought; rebuild required at Phase 25)
- [ ] Image tagged with SHA, no `latest`
- [ ] `docker run` returns `200` on `/api/health` with HOSTNAME unset (proves CMD override works)

### Isolation guard

ECR write only.

---

## Phase 8 — Create VPC, subnets, routes, NAT, security groups

### Task

Single Terraform apply that creates the network graph **including egress** so
later Fargate tasks can actually start.

### Files that will be touched

- `deploy-ecs/terraform/modules/network/`
- `deploy-ecs/terraform/modules/security/`
- `deploy-ecs/terraform/live/prod/main.tf`

### DoD checklist

- [ ] VPC with `enable_dns_support` and `enable_dns_hostnames` true
- [ ] 2 public subnets (different AZs) for ALB
- [ ] 2 private subnets (different AZs) for ECS, RDS, Redis
- [ ] **1 NAT Gateway in 1 public subnet** (B1)
- [ ] Private subnet route table -> NAT Gateway for `0.0.0.0/0`
- [ ] Security groups created: `alb-sg`, `frontend-sg`, `backend-sg`, `db-sg`, `redis-sg`
- [ ] `alb-sg` ingress: 80, 443 from world
- [ ] `frontend-sg` ingress: 3000 from `alb-sg` only
- [ ] `backend-sg` ingress: 8000 from `alb-sg` only
- [ ] `db-sg` ingress: 5432 from `backend-sg` only
- [ ] `redis-sg` ingress: 6379 from `backend-sg` only
- [ ] All service SGs egress 443 to world (ECR/Secrets/Logs over NAT)

### Isolation guard

Network only. No compute.

---

## Phase 9 — Create ALB, listeners, target groups

### Files that will be touched

- `deploy-ecs/terraform/modules/alb/`

### DoD checklist

- [ ] ALB internet-facing in 2 public subnets, attached to `alb-sg`
- [ ] HTTP:80 listener redirects 301 -> HTTPS:443
- [ ] HTTPS:443 listener with default 404 fixed-response
- [ ] Backend target group `a20-backend-tg`: protocol HTTP, port 8000, target type `ip`
- [ ] Backend health check: path `/health`, interval 15, timeout 5, healthy threshold 2, unhealthy threshold 3, matcher `200`
- [ ] Frontend target group `a20-frontend-tg`: protocol HTTP, port 3000, target type `ip`
- [ ] Frontend health check: path `/api/health`, interval 15, timeout 5, healthy threshold 2
- [ ] Host-based listener rules for `api.<domain>` and `app.<domain>` (target by host header; ACM cert attached at Phase 25)
- [ ] Pre-Phase-25 fallback: path `/api/*` -> backend tg, default -> frontend tg, so smoke can run before custom domain

### Isolation guard

ALB only. Targets register at Phase 19/22.

---

## Phase 10 — Create ECS cluster and CloudWatch log groups

### Files that will be touched

- `deploy-ecs/terraform/modules/ecs_cluster/`
- `deploy-ecs/terraform/modules/observability/` (log groups portion)

### DoD checklist

- [ ] Cluster `a20-prod-cluster` exists with `containerInsights` enabled
- [ ] Log group `/ecs/a20-backend` exists with retention `30 days`
- [ ] Log group `/ecs/a20-frontend` exists with retention `30 days`
- [ ] Log group `/ecs/a20-backend-migrate` exists with retention `30 days`
- [ ] Capacity providers default to `FARGATE`

### Isolation guard

Cluster + log groups only. No services yet (B7).

---

## Phase 11 — Create RDS PostgreSQL with deletion_protection

### Files that will be touched

- `deploy-ecs/terraform/modules/database/`

### DoD checklist

- [ ] DB subnet group spans 2 private subnets
- [ ] Instance class as locked in Phase 0
- [ ] `deletion_protection = true` (A6)
- [ ] Storage encrypted with KMS
- [ ] Automated backups: retention 7 days
- [ ] Master credentials generated as random password, written to Secrets Manager (not tfvars)
- [ ] `db-sg` attached
- [ ] Endpoint output recorded

### Isolation guard

DB only. Migrations at Phase 20.

---

## Phase 12 — Enable pgvector

### Task

One-time admin action. Not Terraform.

### DoD checklist

- [ ] Connect via temporary admin path (bastion or SSM-from-task)
- [ ] `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] `\dx` shows `vector`
- [ ] Admin path closed after operation

### Isolation guard

DB DDL only.

---

## Phase 13 — Create ElastiCache Redis/Valkey

### DoD checklist

- [ ] Single small node, in 2 private subnets via subnet group
- [ ] `redis-sg` attached
- [ ] Endpoint output recorded
- [ ] Encryption at rest enabled

### Isolation guard

Cache only.

---

## Phase 14 — Create private S3 bucket

### DoD checklist

- [ ] Bucket `a20-course-assets-prod` exists
- [ ] Public access blocked (all 4 settings true)
- [ ] Versioning enabled
- [ ] Default encryption SSE-S3 or KMS
- [ ] Bucket policy denies non-TLS access

### Isolation guard

S3 only.

---

## Phase 15 — Upload course assets to S3

### DoD checklist

- [ ] Source path verified locally
- [ ] `aws s3 sync` finishes without errors
- [ ] Spot-check object count and total size against expected ~15 GB
- [ ] No credentials leaked in shell history

### Isolation guard

Data plane only.

---

## Phase 16 — Create CloudFront distribution with OAC

### DoD checklist

- [ ] Origin Access Control attached, S3 bucket policy updated to allow only that OAC
- [ ] Default root object configured
- [ ] Range request support verified for an .mp4
- [ ] Cache behavior allows GET, HEAD
- [ ] Distribution domain captured for `CLOUDFRONT_DOMAIN` env

### Isolation guard

CDN only.

---

## Phase 17 — Store production secrets in Secrets Manager

### Files that will be touched

- AWS Secrets Manager (out of band create)

### DoD checklist

- [ ] Secret `a20/prod/backend` JSON contains `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, plus any third-party keys
- [ ] `DATABASE_URL` uses `postgresql+asyncpg://` driver with `?ssl=require`
- [ ] Backend task execution role policy `secretsmanager:GetSecretValue` scoped to this ARN
- [ ] No secret value in tfvars, image, or task definition `environment`
- [ ] Secret values mapped via task definition `secrets[]` block (B4)

### Isolation guard

Secret only.

---

## Phase 18 — Add asset delivery config

### Files that will be touched

- Backend code touching asset URL builder (verify `ASSET_STORAGE_PROVIDER` honored)

### DoD checklist

- [ ] `ASSET_STORAGE_PROVIDER=s3` in production task def env
- [ ] Local dev still works with `ASSET_STORAGE_PROVIDER=local`
- [ ] Backend never proxies video bytes; only emits CloudFront URLs

### Isolation guard

App config only.

---

## Phase 19 — Create backend task definition and ECS service

### Files that will be touched

- `deploy-ecs/terraform/modules/ecs_service/`
- Task definition template under `deploy-ecs/taskdefs/backend.json.tpl`

### DoD checklist

- [ ] All "Before Phase 19" pre-flight items in `HOW_TO_FIX.md` C green
- [ ] Task definition uses Fargate, awsvpc network mode
- [ ] `containerPort = 8000` (B3)
- [ ] `environment` contains only non-secret values
- [ ] `secrets[]` references the Secrets Manager ARN with `valueFrom = <arn>:DATABASE_URL::` style keys (B4)
- [ ] `logConfiguration` -> `awslogs` -> `/ecs/a20-backend`
- [ ] Task uses **task execution role** for secret/log/ECR pulls and **task role** for runtime (B5)
- [ ] Service runs in private subnets, attached to `backend-sg`, `assignPublicIp = DISABLED`
- [ ] Service `health_check_grace_period_seconds >= 60`
- [ ] Service load balancer config points to backend target group on container port 8000
- [ ] `aws ecs wait services-stable` completes
- [ ] Backend target group shows `healthy` count > 0
- [ ] `curl -i http://<alb-dns>/health` returns `200` (note: 5xx through ALB while target healthy means routing rule wrong)

### Isolation guard

Backend service only. Frontend not yet created.

---

## Phase 20 — Run database migrations as one-off ECS task

### Task

Register `a20-backend-migrate` task family using **the same image and secrets**
as the backend service but with `command = ["alembic", "upgrade", "head"]`.
Run it via `aws ecs run-task`. Do **not** add migrations to the service start
command (A4).

### Files that will be touched

- `deploy-ecs/taskdefs/backend-migrate.json.tpl`
- `deploy-ecs/MANUAL_DEPLOY_STEPS.md`

### DoD checklist

- [ ] All "Before Phase 20" pre-flight items in `HOW_TO_FIX.md` C green
- [ ] Migrate task definition shares execution role, task role, secrets, image with backend service
- [ ] `command = ["alembic", "upgrade", "head"]`
- [ ] `essential = true`, no portMappings
- [ ] Run with: `aws ecs run-task --cluster a20-prod-cluster --launch-type FARGATE --network-configuration ... --task-definition a20-backend-migrate`
- [ ] Wait for task to reach `STOPPED` with exit code `0`
- [ ] CloudWatch log shows alembic ran without `invalid interpolation syntax` (A3)
- [ ] `\dt` (or query) confirms `users` and other tables exist
- [ ] Service definition is **not** modified to rerun alembic on every start

### Isolation guard

One-off task only.

---

## Phase 21 — Run bootstrap/import against RDS

### DoD checklist

- [ ] Idempotent bootstrap script exists
- [ ] Run as second one-off ECS task `a20-backend-bootstrap` or via approved admin path
- [ ] Catalog row counts match expected
- [ ] `GET /api/course-sections` (DB-backed) returns `200` with non-empty body (A5)

### Isolation guard

Data only.

---

## Phase 22 — Create frontend task definition and ECS service

### DoD checklist

- [ ] All "Before Phase 22" pre-flight items in `HOW_TO_FIX.md` C green
- [ ] `containerPort = 3000`
- [ ] `environment` includes `HOSTNAME=0.0.0.0` belt-and-suspenders even though Dockerfile CMD enforces it
- [ ] No secrets referenced (frontend has none in v1)
- [ ] Service grace period `>= 120`
- [ ] Service load balancer points to frontend target group on 3000
- [ ] `aws ecs wait services-stable` succeeds
- [ ] Frontend target group `healthy` count > 0
- [ ] `curl -i http://<alb-dns>/api/health` returns `200`

### Isolation guard

Frontend service only.

---

## Phase 23 — Add ECS autoscaling and CloudWatch alarms

### DoD checklist

- [ ] Backend service scales 1–4 on CPU > 70% for 3 minutes
- [ ] Frontend service scales 1–4 on CPU > 70% for 3 minutes
- [ ] Alarms: ECS CPU/memory, ALB 5xx, ALB unhealthy host count, RDS CPU/storage
- [ ] Alarm actions notify SNS topic with operator email

### Isolation guard

Observability only.

---

## Phase 24 — Smoke test on ALB DNS (full pack)

### DoD checklist (all four must pass — A5, B6)

- [ ] `GET <alb>/health` -> `200`
- [ ] `GET <alb>/api/health` -> `200`
- [ ] `GET <alb>/api/course-sections` -> `200` with non-empty array
- [ ] `GET <cloudfront-domain>/<known-asset>` -> `200` and seekable
- [ ] No crash-loop tasks in cluster
- [ ] No 5xx alarms firing

### Isolation guard

Read-only.

---

## Phase 25 — Attach custom domains and rebuild frontend

### DoD checklist

- [ ] ACM cert issued for `app.<domain>`, `api.<domain>`, `cdn.<domain>` (or wildcard) in `ap-southeast-1` for ALB and `us-east-1` for CloudFront
- [ ] ALB HTTPS listener attached to ACM cert
- [ ] CloudFront alternate domain + cert attached
- [ ] Route 53 records: `app` -> ALB alias, `api` -> ALB alias, `cdn` -> CloudFront alias
- [ ] Frontend image **rebuilt** with `NEXT_PUBLIC_API_URL=https://api.<domain>` and redeployed (B8)
- [ ] All Phase 24 smoke checks rerun against final domains

### Isolation guard

Domain cutover only.

---

## Phase 26 — Add budgets and production alarms

### DoD checklist

- [ ] AWS Budget at low/medium/high spend thresholds with email actions
- [ ] CloudFront cache hit rate alarm
- [ ] CloudWatch dashboard linking ECS, ALB, RDS, Redis, CloudFront key metrics

### Isolation guard

Observability only.

---

## Phase 27 — Document rollback and teardown commands

### Files that will be touched

- `deploy-ecs/MANUAL_DEPLOY_STEPS.md` (rollback section)
- `deploy-ecs/PRODUCTION_CHECKLIST.md` (rollback subsection)

### DoD checklist

- [ ] Service rollback procedure documented:
  - `aws ecs update-service --cluster a20-prod-cluster --service a20-backend --task-definition <previous-revision-arn>`
- [ ] Image rollback procedure documented (re-tag previous SHA)
- [ ] Migration rollback caveat documented (alembic downgrade is risky; prefer restore from snapshot)
- [ ] **Teardown precondition documented (A6)**:
  - `aws rds modify-db-instance --db-instance-identifier <id> --no-deletion-protection --apply-immediately`
  - then `terraform destroy`
- [ ] CloudFront pre-destroy step documented (disable distribution, wait `Deployed`, then delete)
- [ ] S3 empty-versions step documented before bucket destroy

### Isolation guard

Documentation only.

---

## Verification Matrix

| Failure mode (HOW_TO_FIX) | Phase covering it | DoD item that proves coverage |
|---|---|---|
| A1 `.dvc` in build context | 1, 6 | `.dockerignore` excludes `.dvc/`; build context size sane |
| A2 Next host binding | 2, 7, 22 | `CMD HOSTNAME=0.0.0.0`; `/api/health` 200 with HOSTNAME unset |
| A3 Alembic `%` interp | 1, 20 | `env.py` escape; migrate task logs show no interp error |
| A4 StartCommand quoting | 20 | Migrations as separate `run-task`, not service command |
| A5 `/health` ≠ schema ready | 21, 24 | Smoke includes DB-backed route |
| A6 RDS deletion protection | 11, 27 | `deletion_protection = true`; teardown runbook disables it first |
| B1 No egress for Fargate | 8 | NAT Gateway provisioned; private route to NAT |
| B2 Health check timing | 9, 19, 22 | Grace period and target group thresholds set |
| B3 Port mismatch | 1, 2, 9, 19, 22 | Same port number in Dockerfile / task def / TG |
| B4 Secrets in env | 17, 19 | Task def `secrets[]` only, never `environment` |
| B5 Role merge | 4, 19 | Two distinct roles in task def |
| B6 services-stable false positive | 19, 22, 24 | Smoke = TG healthy + HTTP 200 + DB route |
| B7 Missing log group | 10, 19 | Log group exists before service apply |
| B8 NEXT_PUBLIC build-time | 7, 25 | Frontend rebuilt at domain cutover |
