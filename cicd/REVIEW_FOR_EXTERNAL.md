# CI/CD Review — External Reviewer Package

> Self-contained document for external review (e.g. GPT). All relevant code excerpts inlined; reviewer does not need repo access.

**Review date**: 2026-05-10
**Repo**: `A20-App-049` (FastAPI 3.12 backend + Next.js 14 frontend)
**Branch**: `feat-terraform-aws`
**Scope**: `cicd/` folder (draft GitHub Actions release pipeline) đối chiếu spec `deploy-ecs/AWS_CICD_GUIDE.md` và state đã deploy thực tế.

---

## 0. What reviewer should evaluate

1. Are the 4 BLOCKER findings correct? Any false positive?
2. Are the proposed fixes (Before/After patches in §6) correct and minimal?
3. Are there additional traps/risks not caught in this review?
4. Is the rollback strategy adequate?
5. Open questions in §9.

---

## 1. Bối cảnh dự án

### Đã deploy
ECS Fargate production deployed manually on 2026-05-09→10. Source: `deploy-ecs/SESSION_JOURNAL.md`.
- 63 Terraform resources via `deploy-ecs/terraform/live/prod` (VPC + NAT, ALB, ECS cluster `a20-prod-cluster`, RDS Postgres 16 `db.t4g.micro`, ElastiCache Redis 7, ECR, S3 + CloudFront, Secrets Manager, IAM/OIDC, observability).
- Region: `ap-southeast-1`. AWS account: `116533674568`.
- 5 backend service revisions, 1 frontend revision. Image SHA: `7deedc0` (with suffixes `-data`, `-units`).
- 11 Secrets Manager keys: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `GMAIL_APP_PASSWORD`, `AI_LOG_API_KEY`, `ADMIN_TOKEN`.
- 3 CloudWatch log groups already created via observability module: `/ecs/a20-backend`, `/ecs/a20-frontend`, `/ecs/a20-backend-migrate`.
- App release loop currently **manual** (PowerShell + `aws ecs ...` CLI).

### Mục đích `cicd/`
Đóng gói release loop manual đó thành GitHub Actions tự động, theo spec ở `deploy-ecs/AWS_CICD_GUIDE.md`. Hiện ở dạng **draft**, chưa promote sang `.github/workflows/`.

### `.github/workflows/` hiện tại
- `ci.yml` — active CI (lint backend/frontend, pytest, type-check).
- `terraform.yml` — dead code: `paths: deploy/terraform/**` (path không tồn tại; thật là `deploy-ecs/terraform/**`).
- `kg-sync.yml` — knowledge graph sync, không liên quan.
- ❌ Không có App Runner, Vercel, Railway. App Runner chỉ là context lịch sử trong PLATFORM_ANALYSIS.md.

---

## 2. Spec target (từ `deploy-ecs/AWS_CICD_GUIDE.md`)

```
push main
  -> CI gate
  -> configure AWS credentials via OIDC
  -> login ECR
  -> docker build/push backend
  -> docker build/push frontend
  -> render backend task definition JSON with new image
  -> register backend revision
  -> update backend ECS service
  -> wait ecs service stable
  -> smoke backend
  -> render frontend task definition JSON with new image
  -> register frontend revision
  -> update frontend ECS service
  -> wait ecs service stable
  -> smoke frontend
```

**Required GitHub vars**: `AWS_REGION`, `AWS_ACCOUNT_ID`, `ECR_BACKEND_REPOSITORY`, `ECR_FRONTEND_REPOSITORY`, `ECS_CLUSTER_NAME`, `ECS_BACKEND_SERVICE_NAME`, `ECS_FRONTEND_SERVICE_NAME`, `BACKEND_TASK_FAMILY`, `FRONTEND_TASK_FAMILY`, `PRODUCTION_BACKEND_URL`, `PRODUCTION_FRONTEND_URL`.

**Required secrets**: `AWS_DEPLOY_ROLE_ARN`.

**Rules**: immutable SHA tag, concurrency `deploy-production`, fail on smoke, image digest + task-def revision in `GITHUB_STEP_SUMMARY`, no AWS access keys.

**Carry-forward traps from prior session** (`HOW_TO_FIX.md`):
- A1: `.dvc/` in build context. A2: Next host binding. A3: Alembic % escape. A4: StartCommand quoting (migration must be one-off task). A5: `/health` ≠ schema ready. A6: RDS `deletion_protection`.
- B1: No egress for Fargate. B2: Health check timing (BE 60s, FE 120s). B3: Port mismatch. B4: Secrets in env (use `secrets[]`). B5: Role merge (execution ≠ task role). B6: `services-stable` false positive (must add TG healthy + HTTP 200 + DB-backed route). B7: Missing log group. B8: `NEXT_PUBLIC_*` baked at build time.

---

## 3. `cicd/` folder structure

```
cicd/
├── ECS_CICD_PLAN.md         # operator-facing plan: vars/secrets list, promotion flow
├── README.md                 # 1-paragraph orientation
├── REVIEW_CHECKLIST.md       # gate items for promotion
├── scripts/
│   ├── render-taskdef.sh     # placeholder substitution for task-def templates
│   ├── run-ecs-task.sh       # one-off Fargate run + wait + exit-code check
│   ├── wait-ecs-service.sh   # services-stable + TG healthy gate
│   ├── smoke-ecs.sh          # HTTP smoke (backend/frontend/db/cloudfront)
│   └── write-deploy-summary.sh  # GITHUB_STEP_SUMMARY writer
├── taskdefs/
│   ├── backend-service.json.tpl    # long-running backend
│   ├── frontend-service.json.tpl   # long-running frontend
│   ├── backend-migrate.json.tpl    # one-off Alembic migration
│   └── backend-bootstrap.json.tpl  # one-off seed/backfill (optional)
└── workflows/
    ├── deploy-ecs-prod.yml         # release pipeline (draft)
    └── terraform-ecs-prod.yml      # Terraform plan/apply (draft)
```

---

## 4. Key code excerpts

### 4.1 `cicd/scripts/smoke-ecs.sh` (51 lines, **complete**)

```bash
#!/usr/bin/env bash
set -euo pipefail

mode="${1:?smoke mode is required: backend|frontend|db|cloudfront}"

http_code() {
  local url="$1"
  curl --silent --show-error --location --output /tmp/smoke-body --write-out "%{http_code}" "$url"
}

require_200() {
  local url="$1"
  local code
  code="$(http_code "$url")"
  if [ "$code" != "200" ]; then
    echo "Smoke failed: $url returned $code" >&2
    cat /tmp/smoke-body >&2 || true
    exit 1
  fi
  echo "Smoke passed: $url"
}

case "$mode" in
  backend)
    : "${PRODUCTION_BACKEND_URL:?PRODUCTION_BACKEND_URL is required}"
    require_200 "${PRODUCTION_BACKEND_URL%/}/health"
    ;;
  frontend)
    : "${PRODUCTION_FRONTEND_URL:?PRODUCTION_FRONTEND_URL is required}"
    require_200 "${PRODUCTION_FRONTEND_URL%/}/api/health"
    require_200 "${PRODUCTION_FRONTEND_URL%/}/"
    ;;
  db)
    : "${PRODUCTION_BACKEND_URL:?PRODUCTION_BACKEND_URL is required}"
    : "${SMOKE_DB_ROUTE:?SMOKE_DB_ROUTE is required}"
    require_200 "${PRODUCTION_BACKEND_URL%/}${SMOKE_DB_ROUTE}"
    ;;
  cloudfront)
    : "${CLOUDFRONT_SMOKE_URL:?CLOUDFRONT_SMOKE_URL is required}"
    code="$(curl --silent --show-error --location --range 0-1023 --output /tmp/smoke-body --write-out "%{http_code}" "$CLOUDFRONT_SMOKE_URL")"
    if [ "$code" != "200" ] && [ "$code" != "206" ]; then
      echo "CloudFront smoke failed: $CLOUDFRONT_SMOKE_URL returned $code" >&2
      exit 1
    fi
    echo "CloudFront smoke passed: $CLOUDFRONT_SMOKE_URL returned $code"
    ;;
  *)
    echo "Unknown smoke mode: $mode" >&2
    exit 2
    ;;
esac
```

### 4.2 `cicd/scripts/run-ecs-task.sh` (39 lines, **complete**)

```bash
#!/usr/bin/env bash
set -euo pipefail

task_definition_arn="${1:?task definition arn is required}"

: "${ECS_CLUSTER_NAME:?ECS_CLUSTER_NAME is required}"
: "${PRIVATE_SUBNET_IDS:?PRIVATE_SUBNET_IDS is required}"
: "${BACKEND_SECURITY_GROUP_ID:?BACKEND_SECURITY_GROUP_ID is required}"

task_arn="$(aws ecs run-task \
  --cluster "$ECS_CLUSTER_NAME" \
  --launch-type FARGATE \
  --task-definition "$task_definition_arn" \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_IDS],securityGroups=[$BACKEND_SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
  --query 'tasks[0].taskArn' \
  --output text)"

if [ -z "$task_arn" ] || [ "$task_arn" = "None" ]; then
  echo "Failed to start ECS task for $task_definition_arn" >&2
  exit 1
fi

echo "Started task: $task_arn"
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER_NAME" --tasks "$task_arn"

exit_code="$(aws ecs describe-tasks \
  --cluster "$ECS_CLUSTER_NAME" \
  --tasks "$task_arn" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"

if [ "$exit_code" != "0" ]; then
  echo "ECS task failed with exit code $exit_code: $task_arn" >&2
  exit 1
fi

echo "ECS task completed successfully: $task_arn"
echo "LAST_ECS_TASK_ARN=$task_arn" >> "${GITHUB_ENV:-/dev/null}"
```

### 4.3 `cicd/scripts/wait-ecs-service.sh` (38 lines, **complete**)

```bash
#!/usr/bin/env bash
set -euo pipefail

cluster_name="${1:?cluster name is required}"
service_name="${2:?service name is required}"
target_group_arn="${3:?target group arn is required}"

aws ecs wait services-stable --cluster "$cluster_name" --services "$service_name"

running_count="$(aws ecs describe-services --cluster "$cluster_name" --services "$service_name" \
  --query 'services[0].runningCount' --output text)"
desired_count="$(aws ecs describe-services --cluster "$cluster_name" --services "$service_name" \
  --query 'services[0].desiredCount' --output text)"

if [ "$running_count" != "$desired_count" ]; then
  echo "Service stable but $running_count/$desired_count" >&2
  exit 1
fi

healthy_count="$(aws elbv2 describe-target-health --target-group-arn "$target_group_arn" \
  --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' --output text)"

if [ "$healthy_count" = "0" ]; then
  echo "No healthy targets for $service_name" >&2
  aws elbv2 describe-target-health --target-group-arn "$target_group_arn" >&2
  exit 1
fi

echo "Service $service_name stable with $healthy_count healthy target(s)."
```

### 4.4 `cicd/scripts/render-taskdef.sh` (30 lines, **complete**)

```bash
#!/usr/bin/env bash
set -euo pipefail

template_path="${1:?template path is required}"
output_path="${2:?output path is required}"

content="$(<"$template_path")"

mapfile -t placeholders < <(grep -o "__[A-Z0-9_][A-Z0-9_]*__" "$template_path" | sed 's/^__//; s/__$//' | sort -u)

for key in "${placeholders[@]}"; do
  if [ -z "${!key:-}" ]; then
    echo "Missing required environment variable: ${key}" >&2
    exit 2
  fi
  value="${!key}"
  content="${content//__${key}__/$value}"
done

if grep -q "__[A-Z0-9_][A-Z0-9_]*__" <<<"$content"; then
  echo "Unresolved template placeholders remain:" >&2
  grep -o "__[A-Z0-9_][A-Z0-9_]*__" <<<"$content" | sort -u >&2
  exit 3
fi

printf '%s\n' "$content" > "$output_path"

if command -v jq >/dev/null 2>&1; then
  jq empty "$output_path"
fi
```

### 4.5 `cicd/taskdefs/backend-bootstrap.json.tpl` (relevant lines)

```json
{
  "family": "a20-backend-bootstrap",     // ← line 2: HARDCODED, không có placeholder
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "__TASK_EXECUTION_ROLE_ARN__",
  "taskRoleArn": "__BACKEND_TASK_ROLE_ARN__",
  "containerDefinitions": [{
    "name": "bootstrap",
    "image": "__IMAGE_URI__",
    "command": ["sh", "-c", "set -e; uv run python scripts/seed_lectures.py; uv run python -m src.scripts.schema_v2.backfill_schema_v2 --apply --report-path reports/backfill.json; ..."],
    "secrets": [
      { "name": "DATABASE_URL", "valueFrom": "__BACKEND_SECRET_ARN__:DATABASE_URL::" },
      { "name": "REDIS_URL", "valueFrom": "__BACKEND_SECRET_ARN__:REDIS_URL::" },
      { "name": "SECRET_KEY", "valueFrom": "__BACKEND_SECRET_ARN__:SECRET_KEY::" }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "__LOG_GROUP__",
        "awslogs-region": "__AWS_REGION__",
        "awslogs-stream-prefix": "bootstrap"
      }
    }
  }]
}
```

### 4.6 `cicd/taskdefs/backend-service.json.tpl` (relevant lines)

```json
"environment": [
  { "name": "PORT", "value": "8000" },
  ...
  { "name": "AWS_S3_BUCKET", "value": "a20-course-assets-prod" },   // ← line 29: HARDCODED
  { "name": "AWS_S3_PREFIX", "value": "courses" },
  { "name": "CLOUDFRONT_DOMAIN", "value": "__CLOUDFRONT_DOMAIN__" },
  ...
]
```

### 4.7 `cicd/workflows/deploy-ecs-prod.yml` — env block + relevant steps

```yaml
name: Deploy ECS Production
on:
  push: { branches: [main] }
  workflow_dispatch:
    inputs:
      deploy_backend: { type: choice, options: ["true","false"], default: "true" }
      deploy_frontend: { type: choice, options: ["true","false"], default: "true" }
      run_migrations: { type: choice, options: ["true","false"], default: "true" }
      run_bootstrap:  { type: choice, options: ["false","true"], default: "false" }
      smoke_cloudfront: { type: choice, options: ["false","true"], default: "false" }
      image_tag: { required: false, default: "" }   # rollback path

permissions: { contents: read, id-token: write }
concurrency: { group: deploy-production, cancel-in-progress: false }

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  deploy:
    runs-on: ubuntu-latest
    environment: production
    needs: ci
    env:
      AWS_REGION: ${{ vars.AWS_REGION }}
      AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      # ...11 more vars
      CLOUDFRONT_DOMAIN: ${{ vars.CLOUDFRONT_DOMAIN }}   # ← line 76
      BACKEND_SECRET_ARN: ${{ secrets.BACKEND_SECRET_ARN }}
      # ...8 more secrets

    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with: { role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}, aws-region: ${{ env.AWS_REGION }} }
      - uses: aws-actions/amazon-ecr-login@v2

      # Step 1: resolve image tag (SHA or rollback)
      # Step 2: docker build/push backend
      # Step 3: docker build/push frontend (build args: NEXT_PUBLIC_API_URL, API_INTERNAL_URL)

      - name: Deploy backend service
        if: steps.tag.outputs.deploy_backend == 'true'
        run: |
          IMAGE_URI="$BACKEND_IMAGE" LOG_GROUP="/ecs/${ECS_BACKEND_SERVICE_NAME}" \
            bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-service.json.tpl /tmp/backend-service.json
          backend_arn="$(aws ecs register-task-definition --cli-input-json file:///tmp/backend-service.json --query 'taskDefinition.taskDefinitionArn' --output text)"
          aws ecs update-service --cluster "$ECS_CLUSTER_NAME" --service "$ECS_BACKEND_SERVICE_NAME" --task-definition "$backend_arn" --force-new-deployment
          bash cicd/scripts/wait-ecs-service.sh "$ECS_CLUSTER_NAME" "$ECS_BACKEND_SERVICE_NAME" "$BACKEND_TARGET_GROUP_ARN"
          bash cicd/scripts/smoke-ecs.sh backend

      - name: Run migrations
        if: steps.tag.outputs.run_migrations == 'true' && steps.tag.outputs.deploy_backend == 'true'
        run: |
          IMAGE_URI="$BACKEND_IMAGE" LOG_GROUP="/ecs/${MIGRATE_TASK_FAMILY}" \
            bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-migrate.json.tpl /tmp/backend-migrate.json
          migrate_arn="$(aws ecs register-task-definition --cli-input-json file:///tmp/backend-migrate.json --query 'taskDefinition.taskDefinitionArn' --output text)"
          bash cicd/scripts/run-ecs-task.sh "$migrate_arn"
          bash cicd/scripts/smoke-ecs.sh db

      - name: Run bootstrap
        if: steps.tag.outputs.run_bootstrap == 'true' && steps.tag.outputs.deploy_backend == 'true'
        run: |
          IMAGE_URI="$BACKEND_IMAGE" LOG_GROUP="/ecs/${MIGRATE_TASK_FAMILY}" \   # ← line 210: BUG — dùng MIGRATE family cho bootstrap
            bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-bootstrap.json.tpl /tmp/backend-bootstrap.json
          bootstrap_arn="$(aws ecs register-task-definition --cli-input-json file:///tmp/backend-bootstrap.json --query 'taskDefinition.taskDefinitionArn' --output text)"
          bash cicd/scripts/run-ecs-task.sh "$bootstrap_arn"
          bash cicd/scripts/smoke-ecs.sh db

      # Step 4: deploy frontend (similar to backend)

      - name: Optional CloudFront smoke
        if: steps.tag.outputs.smoke_cloudfront == 'true'
        run: bash cicd/scripts/smoke-ecs.sh cloudfront     # ← Bug B1: cần CLOUDFRONT_SMOKE_URL nhưng workflow không truyền

      - name: Write deployment summary
        if: always()
        run: bash cicd/scripts/write-deploy-summary.sh
```

### 4.8 `.github/workflows/ci.yml` — path filter (relevant)

```yaml
on:
  push: { branches: ["**"] }
  pull_request: { branches: [main] }
  workflow_call:

jobs:
  changes:
    runs-on: [self-hosted, phoenix-runner-02]   # ← N3: self-hosted only
    steps:
      - uses: dorny/paths-filter@v3
        with:
          filters: |
            backend:
              - "src/**"
              - "tests/**"
              - "alembic/**"
              ...
            frontend:
              - "frontend/**"
            repo_config:
              - ".github/workflows/**"
              - "deploy/**"           # ← B2: stale path; thật là "deploy-ecs/**"
              - ".gitignore"
              - "AGENTS.md"
            # ❌ thiếu "cicd/**" và "deploy-ecs/**"
```

---

## 5. Đối chiếu spec ↔ thực tế ↔ `cicd/`

| Yêu cầu | Spec deploy-ecs | Thực tế đã chạy | `cicd/` impl | Verdict |
|---|---|---|---|---|
| Region | ap-southeast-1 | acct 116533674568 | `${vars.AWS_REGION}` | ✅ |
| OIDC, no AWS keys | bắt buộc | trust policy `a20-ai-thuc-chien/A20-App-049` | `configure-aws-credentials@v4 + role-to-assume` | ✅ |
| Immutable SHA tag | bắt buộc | `7deedc0` (+`-data`,`-units`) | `tag=${GITHUB_SHA}` | ✅ |
| Secrets via `secrets[]` | trap B4 | 11 keys Secrets Manager | `valueFrom: __BACKEND_SECRET_ARN__:KEY::` | ✅ |
| Role split exec/task | trap B5 | 4 role qua `iam_oidc` | tpl tách rõ | ✅ |
| Migration one-off | trap A4 | Bài 6 manual | `run-ecs-task.sh + backend-migrate.json.tpl` | ✅ |
| Smoke 4-layer | trap B6 | Bài 7 verify đủ | `wait-ecs-service.sh + smoke-ecs.sh` | ✅ |
| Health grace BE60s/FE120s | trap B2 | Set ở Terraform service | tpl không override | ✅ |
| CW log group có trước | trap B7 | 3 log group đã tạo | Workflow không pre-flight | ⚠️ N4 |
| `AGENT_GRAPH_CHECKPOINTER_SETUP=false` | Bài 13a fix | Set qua Terraform | tpl env có | ✅ |
| Frontend `NEXT_PUBLIC_API_URL` build-time | trap B8 | Trỏ ALB DNS | Build args `=$PRODUCTION_BACKEND_URL` | ✅ if vars updated |
| ECR immutable + scan | `ecr` module | Đã set | Workflow không kiểm | ✅ |
| Rollback | re-register revision | Manual CLI | Input `image_tag` redeploy | ✅ |
| Bootstrap (seed+backfill) | one-off | Bài 8-11 manual | flag `run_bootstrap` | ✅ logic; ❌ template B3 |

---

## 6. BLOCKER — Before/After patches

> **STATUS (2026-05-10): All 4 blockers FIXED in commit. Patches applied as described below.**

### B1. CloudFront smoke env var mismatch ✅ FIXED

**Problem**: `smoke-ecs.sh:39` requires `CLOUDFRONT_SMOKE_URL`. Workflow only passes `CLOUDFRONT_DOMAIN` (bare domain). Step `Optional CloudFront smoke` (line 254-257) will fail immediately when `smoke_cloudfront=true` with `CLOUDFRONT_SMOKE_URL is required`.

**Proposed fix**: add new var `CLOUDFRONT_SMOKE_URL` (full URL pointing to a known-uploaded asset, e.g. `https://dxxx.cloudfront.net/courses/cs230/lectures/L01.pdf`).

**Patch**:
```diff
# cicd/workflows/deploy-ecs-prod.yml line 76 vicinity
       CLOUDFRONT_DOMAIN: ${{ vars.CLOUDFRONT_DOMAIN }}
+      CLOUDFRONT_SMOKE_URL: ${{ vars.CLOUDFRONT_SMOKE_URL }}
```

Update `cicd/ECS_CICD_PLAN.md` to list `CLOUDFRONT_SMOKE_URL` as required var.

**Acceptance**: `workflow_dispatch smoke_cloudfront=true` returns 200 or 206 from the configured asset URL.

---

### B2. CI doesn't trigger on `cicd/**` or `deploy-ecs/**` changes ✅ FIXED

**Problem**: `ci.yml` `repo_config` filter lists `deploy/**` (path doesn't exist; real path is `deploy-ecs/**`) and missing `cicd/**`. Edits to task-def templates or Terraform modules won't get CI lint/validate.

**Patch**:
```diff
             repo_config:
               - ".github/workflows/**"
-              - "deploy/**"
+              - "cicd/**"
+              - "deploy-ecs/**"
               - ".gitignore"
               - "AGENTS.md"
```

**Acceptance**: opening a PR that only touches `cicd/scripts/*.sh` triggers `ci.yml`'s `repo-config` job.

---

### B3. Bootstrap task family hardcoded ✅ FIXED

**Problem**: `backend-bootstrap.json.tpl:2` hardcodes `"family": "a20-backend-bootstrap"` instead of `__BOOTSTRAP_TASK_FAMILY__`. Workflow doesn't declare `BOOTSTRAP_TASK_FAMILY` (cf. `MIGRATE_TASK_FAMILY` at line 72). Breaks 100% template-driven invariant; not reusable for staging.

**Patch 1** — `cicd/taskdefs/backend-bootstrap.json.tpl`:
```diff
 {
-  "family": "a20-backend-bootstrap",
+  "family": "__BOOTSTRAP_TASK_FAMILY__",
   "networkMode": "awsvpc",
```

**Patch 2** — `cicd/workflows/deploy-ecs-prod.yml` env block:
```diff
       MIGRATE_TASK_FAMILY: ${{ vars.MIGRATE_TASK_FAMILY }}
+      BOOTSTRAP_TASK_FAMILY: ${{ vars.BOOTSTRAP_TASK_FAMILY }}
```

GitHub repo: add `vars.BOOTSTRAP_TASK_FAMILY = a20-backend-bootstrap`.

**Acceptance**: render-taskdef test produces JSON with `"family": "a20-backend-bootstrap"` (or any other value when var changed) and zero unresolved placeholders.

---

### B4. Bootstrap step writes to wrong log group ✅ FIXED

**Problem**: `deploy-ecs-prod.yml:210` passes `LOG_GROUP="/ecs/${MIGRATE_TASK_FAMILY}"` for the bootstrap step (copy-paste error from migrate step). Bootstrap is a different task family. SESSION_JOURNAL confirms only 3 log groups created: `/ecs/a20-backend`, `/ecs/a20-frontend`, `/ecs/a20-backend-migrate`. **No log group for bootstrap exists yet**.

**Patch 1** — `cicd/workflows/deploy-ecs-prod.yml` line 210:
```diff
       - name: Run bootstrap
         if: ${{ steps.tag.outputs.run_bootstrap == 'true' && steps.tag.outputs.deploy_backend == 'true' }}
         run: |
           IMAGE_URI="$BACKEND_IMAGE" \
-          LOG_GROUP="/ecs/${MIGRATE_TASK_FAMILY}" \
+          LOG_GROUP="/ecs/${BOOTSTRAP_TASK_FAMILY}" \
           bash cicd/scripts/render-taskdef.sh \
             cicd/taskdefs/backend-bootstrap.json.tpl \
             /tmp/backend-bootstrap.json
```

**Patch 2** — `deploy-ecs/terraform/modules/observability/main.tf` (add 4th log group):
```hcl
resource "aws_cloudwatch_log_group" "backend_bootstrap" {
  name              = "/ecs/${var.bootstrap_task_family}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
```
And expose `bootstrap_task_family` as a variable, plumb from root module.

**Acceptance**: after `terraform apply`, log group `/ecs/a20-backend-bootstrap` exists; bootstrap task run streams logs there.

---

## 7. Should-fix (non-blocking)

### N1. S3 bucket hardcoded
`backend-service.json.tpl:29` has `"value": "a20-course-assets-prod"`. Replace with `__AWS_S3_BUCKET__`, plumb `vars.AWS_S3_BUCKET` through workflow.

### N2. `CLOUDFRONT_DOMAIN` placeholder verification
Verify `vars.CLOUDFRONT_DOMAIN` is set in GitHub repo settings before first run (already populated per SESSION_JOURNAL Bài 8).

### N3. CI runs on self-hosted `phoenix-runner-02` only
`ci.yml:31` `runs-on: [self-hosted, phoenix-runner-02]`. If runner offline → deploy blocks at `needs: ci`. Recommend `ubuntu-latest` for the gating job, or set up backup runner.

### N4. Pre-flight CloudWatch log group check
Add idempotent `aws logs create-log-group --log-group-name "$LOG_GROUP" 2>/dev/null || true` before each `register-task-definition` call. Low risk now (Terraform created them) but defends against staging clones.

### N5. `run-ecs-task.sh` doesn't surface logs on failure
After `aws ecs wait tasks-stopped`, when `exit_code != 0`, fetch and print last 10 minutes of CloudWatch logs:
```bash
if [ "$exit_code" != "0" ]; then
  echo "=== Last 10min of $LOG_GROUP ===" >&2
  aws logs tail "$LOG_GROUP" --since 10m >&2 || true
  exit 1
fi
```
Justification: SESSION_JOURNAL had 19 issues, many requiring CloudWatch log inspection (Issue 14 chat 504, Issue 7 migration A3 % escape).

### N6. Delete `.github/workflows/terraform.yml`
Stale: path filter `deploy/terraform/**` doesn't match real `deploy-ecs/terraform/**`. Will be replaced by `cicd/workflows/terraform-ecs-prod.yml` on promotion.

---

## 8. Out-of-scope (not part of release loop)

1. Phase 25 cutover domain: HTTPS listener + ACM cert + Route 53 alias + frontend rebuild with production `NEXT_PUBLIC_API_URL`. Currently using ALB DNS.
2. pgvector DDL, asset upload S3, Secrets Manager initial seed: 1-time manual.
3. Bootstrap data flows: already executed manually, covered by template, gated behind `run_bootstrap=true` flag.

---

## 9. Open questions for reviewer

1. **Rollback**: is `image_tag` input adequate, or do we need an explicit `rollback-to-revision-N` workflow that just calls `update-service --task-definition <prev-arn>` without rebuilding?
2. **Concurrency**: backend deploy → migrations → frontend deploy is sequential. Acceptable, or worth parallelizing backend+frontend after migrations succeed?
3. **Approval gate**: `environment: production` requires GitHub Environment approval. Should we also add an explicit pause between backend deploy and migrations (current flow auto-runs migrations)?
4. **Log retention**: SESSION_JOURNAL says 7 days. For prod debugging, is this enough? Some teams keep 30 days.
5. **Observability beyond logs**: no X-Ray, no SNS alerts on deploy failure. Acceptable for v1?
6. **Terraform drift**: `ecs_service` module has `lifecycle { ignore_changes = [task_definition] }` so GitHub Actions can register revisions independently. Reviewer: any concerns about silent drift between Terraform-known and actual task-def?
7. **Multi-env**: only `production` env defined. Staging path?
8. **Secret rotation**: 11 secrets in Secrets Manager are static. Rotation schedule defined?

---

## 10. Verification plan after fixes

```bash
# 1. Syntax
bash -n cicd/scripts/*.sh
python -c "import yaml; yaml.safe_load(open('cicd/workflows/deploy-ecs-prod.yml'))"
python -c "import yaml; yaml.safe_load(open('cicd/workflows/terraform-ecs-prod.yml'))"
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

# 2. Render dry-run (must produce valid JSON, zero placeholders)
IMAGE_URI=test \
BACKEND_SECRET_ARN=arn:test \
TASK_EXECUTION_ROLE_ARN=arn:exec \
BACKEND_TASK_ROLE_ARN=arn:task \
BOOTSTRAP_TASK_FAMILY=a20-backend-bootstrap \
LOG_GROUP=/ecs/test \
AWS_REGION=ap-southeast-1 \
bash cicd/scripts/render-taskdef.sh cicd/taskdefs/backend-bootstrap.json.tpl /tmp/bs.json
jq . /tmp/bs.json

# 3. Promote workflows
cp cicd/workflows/deploy-ecs-prod.yml .github/workflows/
cp cicd/workflows/terraform-ecs-prod.yml .github/workflows/
rm .github/workflows/terraform.yml   # N6

# 4. Dry test (all deploy flags false → workflow runs to summary, no service touched)
gh workflow run "Deploy ECS Production" \
  --field deploy_backend=false --field deploy_frontend=false \
  --field run_migrations=false --field run_bootstrap=false \
  --field smoke_cloudfront=false

# 5. Wet test (full deploy on test branch or production with rollback ready)
gh workflow run "Deploy ECS Production" \
  --field deploy_backend=true --field deploy_frontend=true \
  --field run_migrations=true
```

**AWS Console checks after wet test**:
- ECR: new image with tag `<sha>`.
- ECS: backend task-def revision ≥6, frontend ≥2 (next after Bài 13b/14).
- Service event log: "service has reached a steady state".
- ALB target group: ≥1 healthy target.
- CloudWatch: new stream in `/ecs/a20-backend` + `/ecs/a20-backend-migrate` (+ `/ecs/a20-backend-bootstrap` if run).
- Smoke endpoints `/health`, `/api/course-sections`, `/api/health`, `/` return 200.

---

## 11. Summary

| Item | Count | Status |
|---|---:|---|
| Blockers | 4 | Must fix before promotion |
| Should-fix | 6 | Non-blocking but recommended |
| Out-of-scope | 3 | Manual / cutover phase |
| Spec conformance | 13/14 | One gap: pre-flight log group (N4) |
| Open questions | 8 | Reviewer input requested |

`cicd/` package is **architecturally sound** and aligned with `deploy-ecs/AWS_CICD_GUIDE.md` spec. Blockers are mechanical errors (template hardcoding, env var mismatch) — fixes are minimal (≤30 lines total). Recommend proceeding with patches, then promote to `.github/workflows/` and run the dry test before first production auto-deploy.
