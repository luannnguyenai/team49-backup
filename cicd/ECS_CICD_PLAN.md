# ECS CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reviewable ECS CI/CD package that can be promoted into active GitHub Actions workflows after review.

**Architecture:** Terraform owns the stable ECS infrastructure under `deploy-ecs/terraform`. GitHub Actions owns app releases by building immutable ECR images, registering task definition revisions, updating ECS services, running one-off migration tasks, and smoke testing through the ALB.

**Tech Stack:** GitHub Actions, AWS OIDC, Amazon ECR, Amazon ECS Fargate, ALB, Terraform, Bash, Docker, FastAPI, Next.js.

---

## Current Repo Findings

- Active CI exists at `.github/workflows/ci.yml` and already supports `workflow_call`.
- Active deploy workflow `.github/workflows/deploy.yml` is frozen legacy deploy and does not deploy to AWS.
- Active Terraform workflow `.github/workflows/terraform.yml` targets `deploy/terraform`, not `deploy-ecs/terraform`.
- `deploy-ecs/terraform/live/prod` is split into Stage 1 foundation and Stage 2 ECS services through `enable_services`, `backend_image`, `frontend_image`, and `backend_secret_arn`.
- `deploy-ecs/terraform/modules/ecs_service/main.tf` ignores `task_definition` drift, which allows GitHub Actions to register later task definition revisions after initial service creation.
- `deploy-ecs/taskdefs/*.json` are rendered operational artifacts with account IDs, concrete image tags, and secret ARNs. They must not be reused as generic CI templates.

## Files To Add

- Create: `cicd/README.md`
- Create: `cicd/ECS_CICD_PLAN.md`
- Create: `cicd/REVIEW_CHECKLIST.md`
- Create: `cicd/workflows/deploy-ecs-prod.yml`
- Create: `cicd/workflows/terraform-ecs-prod.yml`
- Create: `cicd/taskdefs/backend-service.json.tpl`
- Create: `cicd/taskdefs/frontend-service.json.tpl`
- Create: `cicd/taskdefs/backend-migrate.json.tpl`
- Create: `cicd/taskdefs/backend-bootstrap.json.tpl`
- Create: `cicd/scripts/render-taskdef.sh`
- Create: `cicd/scripts/run-ecs-task.sh`
- Create: `cicd/scripts/wait-ecs-service.sh`
- Create: `cicd/scripts/smoke-ecs.sh`
- Create: `cicd/scripts/write-deploy-summary.sh`

## Required GitHub Production Variables

```text
AWS_REGION=ap-southeast-1
AWS_ACCOUNT_ID=<account-id>
ECR_BACKEND_REPOSITORY=a20-backend
ECR_FRONTEND_REPOSITORY=a20-frontend
ECS_CLUSTER_NAME=a20-prod-cluster
ECS_BACKEND_SERVICE_NAME=a20-backend
ECS_FRONTEND_SERVICE_NAME=a20-frontend
BACKEND_TASK_FAMILY=a20-backend
FRONTEND_TASK_FAMILY=a20-frontend
MIGRATE_TASK_FAMILY=a20-backend-migrate
BOOTSTRAP_TASK_FAMILY=a20-backend-bootstrap
PRODUCTION_BACKEND_URL=<ALB-or-api-url>
PRODUCTION_FRONTEND_URL=<ALB-or-app-url>
SMOKE_DB_ROUTE=/api/course-sections
CLOUDFRONT_DOMAIN=<cloudfront-domain-without-scheme>
CLOUDFRONT_SMOKE_URL=<full-https-url-to-known-asset>
```

## Required GitHub Production Secrets

```text
AWS_DEPLOY_ROLE_ARN=<gha deploy role arn>
AWS_TERRAFORM_ROLE_ARN=<gha terraform role arn>
TF_BACKEND_HCL_PROD=<deploy-ecs backend.hcl content>
TFVARS_PROD=<deploy-ecs terraform.tfvars content>
BACKEND_SECRET_ARN=<Secrets Manager backend secret arn>
TASK_EXECUTION_ROLE_ARN=<ECS task execution role arn>
BACKEND_TASK_ROLE_ARN=<backend task role arn>
FRONTEND_TASK_ROLE_ARN=<frontend task role arn>
PRIVATE_SUBNET_IDS=<comma-separated private subnet ids>
BACKEND_SECURITY_GROUP_ID=<backend ECS security group id>
BACKEND_TARGET_GROUP_ARN=<backend target group arn>
FRONTEND_TARGET_GROUP_ARN=<frontend target group arn>
```

## Task 1: Review Package Skeleton

**Files:**
- Create: `cicd/README.md`
- Create: `cicd/ECS_CICD_PLAN.md`
- Create: `cicd/REVIEW_CHECKLIST.md`

- [ ] **Step 1: Confirm review package is isolated**

Run:

```bash
test -d cicd
test ! -d .github/workflows/cicd
```

Expected: both commands exit `0`.

- [ ] **Step 2: Confirm no workflow is active yet**

Run:

```bash
find cicd/workflows -maxdepth 1 -type f -name "*.yml" -print
find .github/workflows -maxdepth 1 -type f -name "*ecs*" -print
```

Expected: ECS workflow drafts appear under `cicd/workflows`; no active ECS workflow appears under `.github/workflows` until promotion.

## Task 2: ECS Deploy Workflow Draft

**Files:**
- Create: `cicd/workflows/deploy-ecs-prod.yml`
- Create: `cicd/scripts/render-taskdef.sh`
- Create: `cicd/scripts/wait-ecs-service.sh`
- Create: `cicd/scripts/smoke-ecs.sh`
- Create: `cicd/scripts/write-deploy-summary.sh`

- [ ] **Step 1: Validate YAML syntax**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
for path in Path("cicd/workflows").glob("*.yml"):
    yaml.safe_load(path.read_text(encoding="utf-8"))
    print(f"parsed {path}")
PY
```

Expected: both workflow drafts parse.

- [ ] **Step 2: Validate shell syntax**

Run:

```bash
bash -n cicd/scripts/*.sh
```

Expected: exits `0`.

- [ ] **Step 3: Confirm deployment gates**

Run:

```bash
rg -n "services-stable|describe-target-health|smoke-ecs|run_migrations|GITHUB_STEP_SUMMARY" cicd/workflows cicd/scripts
```

Expected: matches show ECS stable wait, target health checks, smoke tests, migration gating, and deploy summary output.

## Task 3: Terraform ECS Workflow Draft

**Files:**
- Create: `cicd/workflows/terraform-ecs-prod.yml`

- [ ] **Step 1: Confirm ECS Terraform path**

Run:

```bash
rg -n "deploy-ecs/terraform" cicd/workflows/terraform-ecs-prod.yml
```

Expected: workflow targets `deploy-ecs/terraform`, not `deploy/terraform`.

- [ ] **Step 2: Confirm apply is manual gated**

Run:

```bash
rg -n "workflow_dispatch|inputs.apply == 'true'|terraform apply" cicd/workflows/terraform-ecs-prod.yml
```

Expected: apply only runs for manual dispatch with `apply=true`.

## Task 4: Task Definition Templates

**Files:**
- Create: `cicd/taskdefs/backend-service.json.tpl`
- Create: `cicd/taskdefs/frontend-service.json.tpl`
- Create: `cicd/taskdefs/backend-migrate.json.tpl`
- Create: `cicd/taskdefs/backend-bootstrap.json.tpl`

- [ ] **Step 1: Render backend service template with fake values**

Run:

```bash
IMAGE_URI=123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/a20-backend:test \
TASK_EXECUTION_ROLE_ARN=arn:aws:iam::123456789012:role/exec \
BACKEND_TASK_ROLE_ARN=arn:aws:iam::123456789012:role/backend \
BACKEND_SECRET_ARN=arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:a20/prod/backend \
AWS_REGION=ap-southeast-1 \
BACKEND_TASK_FAMILY=a20-backend \
LOG_GROUP=/ecs/a20-backend \
bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-service.json.tpl /tmp/backend.json
jq empty /tmp/backend.json
```

Expected: `jq empty` exits `0`.

- [ ] **Step 2: Confirm secrets are not in environment**

Run:

```bash
rg -n '"name": "(DATABASE_URL|REDIS_URL|SECRET_KEY)"' cicd/taskdefs/backend-service.json.tpl
rg -n '"environment".*(DATABASE_URL|REDIS_URL|SECRET_KEY)' cicd/taskdefs
```

Expected: first command finds secrets under `secrets`; second command finds nothing.

## Task 5: Promotion Into Active Workflows

**Files:**
- Modify after review only: `.github/workflows/deploy-ecs-prod.yml`
- Modify after review only: `.github/workflows/terraform-ecs-prod.yml`
- Optional modify after review only: `.github/workflows/ci.yml`

- [ ] **Step 1: Copy reviewed workflow drafts**

Run after review approval:

```bash
cp cicd/workflows/deploy-ecs-prod.yml .github/workflows/deploy-ecs-prod.yml
cp cicd/workflows/terraform-ecs-prod.yml .github/workflows/terraform-ecs-prod.yml
```

Expected: active ECS workflow files exist.

- [ ] **Step 2: Update CI path filters**

Modify `.github/workflows/ci.yml` so `repo_config` includes:

```yaml
              - "deploy-ecs/**"
              - "cicd/**"
```

Expected: CI validates changes to ECS deploy docs and review package.

- [ ] **Step 3: Keep legacy deploy frozen**

Run:

```bash
rg -n "Legacy Deploy|Frozen|apprunner|deploy-ecs-prod" .github/workflows
```

Expected: `.github/workflows/deploy.yml` remains frozen; ECS deploy lives in its own active workflow.

## Review Gates

- No `latest` image tag is used.
- No AWS long-lived access key appears in workflows.
- No App Runner API call appears in `cicd/`.
- No migration command appears in backend service startup.
- `aws ecs wait services-stable` is paired with target health and HTTP smoke.
- Smoke includes a DB-backed route, not only `/health`.
- Frontend image build receives `NEXT_PUBLIC_API_URL` and `API_INTERNAL_URL`.
- Task definition templates use distinct task execution role and task role.

## Assumptions

- ECS services are created once by Terraform Stage 2 before app release workflows become the source of truth for task definition revisions.
- `cicd/` files are review artifacts until copied into `.github/workflows`.
- Existing `deploy-ecs/taskdefs/*.json` files are operational snapshots and should remain separate from reusable CI templates.
- Rolling deployment is the v1 release strategy.
