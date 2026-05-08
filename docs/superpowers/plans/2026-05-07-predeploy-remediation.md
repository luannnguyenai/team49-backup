# Predeploy Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the remaining deployment blockers before executing the full AWS production deploy.

**Architecture:** Keep the target architecture from `deploy/DEPLOYMENT_PLAN.md`: AWS App Runner for frontend/backend, ECR images, RDS PostgreSQL with pgvector, ElastiCache Redis/Valkey, S3 private assets, CloudFront delivery, Secrets Manager, Route 53, ACM, CloudWatch, and GitHub Actions with AWS OIDC. This plan only fixes predeploy gaps and does not provision production resources.

**Tech Stack:** GitHub Actions, AWS OIDC, ECR, App Runner, FastAPI, Python 3.12, Next.js 14, Docker, Alembic, PostgreSQL/RDS, S3, CloudFront.

---

## File Map

- `.github/workflows/ci.yml`: Make CI reusable by deploy workflow, align Python with project runtime, keep backend/frontend validation gates.
- `.github/workflows/deploy.yml`: Replace Vercel/Railway/Supabase deploy with AWS OIDC, ECR image build/push, App Runner update, and smoke tests.
- `deploy/DEPLOYMENT_PLAN.md`: Record decisions that affect sequencing, especially CI/CD, frontend rebuild timing, and migration execution environment.
- `deploy/MANUAL_DEPLOY_STEPS.md`: Correct manual order so backend/App Runner URL exists before final frontend image build, and define the RDS-private migration path.
- `deploy/ENVIRONMENT_MATRIX.md`: Document GitHub Actions variables/secrets and runtime values needed by AWS App Runner.
- `deploy/AWS_CICD_GUIDE.md`: Keep the OIDC role, GitHub environment, deploy variables, and rollback workflow aligned with the actual workflow.
- `deploy/PRODUCTION_CHECKLIST.md`: Add final predeploy gates so the team cannot mark production ready while workflow/provider mismatches remain.
- `Dockerfile`: Verify only; backend already binds `0.0.0.0:${PORT:-8000}`.
- `frontend/Dockerfile`: Verify only; frontend standalone server already reads runtime `PORT`.

---

### Task 1: Freeze Current Deploy Mismatch

**Files:**
- Modify: `remaining tasks/cicd/current-state.md`
- Modify: `deploy/DEPLOYMENT_PLAN.md`

- [ ] **Step 1: Record the current mismatch**

Add a section to `remaining tasks/cicd/current-state.md`:

```markdown
## Production Deploy Mismatch - 2026-05-07

Current `.github/workflows/deploy.yml` still targets:

- Frontend: Vercel
- Backend: Railway
- Database migrations: Supabase

Production target is now full AWS:

- Frontend: AWS App Runner from ECR image
- Backend: AWS App Runner from ECR image
- Database: RDS PostgreSQL with pgvector
- Cache: ElastiCache Redis OSS or Valkey
- Assets: private S3 bucket through CloudFront
- CI/CD auth: GitHub Actions OIDC role, no long-lived AWS access keys

Decision: do not run the current production deploy workflow for the AWS deployment. Replace it before any merge-to-main production deploy.
```

- [ ] **Step 2: Add a deploy gate note**

In `deploy/DEPLOYMENT_PLAN.md`, under Phase 2.1 DoD, ensure this item exists:

```markdown
- [ ] Existing Vercel/Railway/Supabase production deploy workflow is marked unsafe for the AWS target until Phase 2.4 replaces it.
```

- [ ] **Step 3: Verify**

Run:

```bash
rg -n "Vercel|Railway|Supabase|full AWS|unsafe" "remaining tasks/cicd/current-state.md" deploy/DEPLOYMENT_PLAN.md
```

Expected: the old providers are documented only as current mismatch, not as the target production path.

- [ ] **Step 4: Commit**

```bash
git add "remaining tasks/cicd/current-state.md" deploy/DEPLOYMENT_PLAN.md
git commit -m "docs: record aws deploy workflow mismatch"
```

---

### Task 2: Make CI Reusable and Runtime-Aligned

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `deploy/PRODUCTION_CHECKLIST.md`

- [ ] **Step 1: Add reusable workflow trigger**

Update `.github/workflows/ci.yml`:

```yaml
on:
  push:
    branches-ignore:
      - main
  pull_request:
    branches:
      - main
  workflow_call:
```

- [ ] **Step 2: Align Python version**

Replace both GitHub Actions Python versions in `.github/workflows/ci.yml`:

```yaml
python-version: "3.12"
```

- [ ] **Step 3: Keep frontend build gate**

Confirm the frontend job still runs:

```yaml
- name: Next.js build (dry-run)
  env:
    NEXT_PUBLIC_API_URL: http://localhost:8000
  run: npm run build
```

- [ ] **Step 4: Verify workflow structure**

Run:

```bash
rg -n "workflow_call|python-version: \"3.12\"|npm run build" .github/workflows/ci.yml
```

Expected:

- `workflow_call` appears once.
- Python 3.12 appears in backend lint and backend test jobs.
- Frontend dry-run build remains present.

- [ ] **Step 5: Run local validation where available**

Run:

```bash
uv run pytest tests/test_docker_compose_healthcheck.py -q
npm test -- --run tests/unit/app-metadata.test.ts
```

Expected: both pass, or local environment limitation is documented before proceeding.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml deploy/PRODUCTION_CHECKLIST.md
git commit -m "ci: align reusable workflow with production runtime"
```

---

### Task 3: Replace Production Deploy Workflow with AWS App Runner Flow

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Modify: `deploy/AWS_CICD_GUIDE.md`
- Modify: `deploy/ENVIRONMENT_MATRIX.md`

- [ ] **Step 1: Replace provider-specific comments**

Remove references to Vercel, Railway, and Supabase as deploy targets from `.github/workflows/deploy.yml`. The header should identify:

```yaml
# Deploy targets:
#   Frontend -> AWS App Runner from ECR image
#   Backend  -> AWS App Runner from ECR image
#   Database -> RDS PostgreSQL, migrations run through approved admin path
```

- [ ] **Step 2: Add AWS permissions**

Add top-level permissions:

```yaml
permissions:
  contents: read
  id-token: write
```

- [ ] **Step 3: Keep CI gate**

Keep the reusable CI gate:

```yaml
jobs:
  ci-gate:
    name: "CI gate (lint + tests)"
    uses: ./.github/workflows/ci.yml
```

- [ ] **Step 4: Add AWS credential setup**

Use OIDC role assumption in deploy jobs:

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
    aws-region: ${{ vars.AWS_REGION }}
```

- [ ] **Step 5: Build and push backend image**

Backend deploy job must:

```bash
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$ECR_BACKEND_REPOSITORY:$GITHUB_SHA" .
docker tag "$ECR_BACKEND_REPOSITORY:$GITHUB_SHA" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPOSITORY:$GITHUB_SHA"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPOSITORY:$GITHUB_SHA"
```

- [ ] **Step 6: Update backend App Runner**

Update App Runner with the pushed image:

```bash
aws apprunner update-service \
  --service-arn "$APP_RUNNER_BACKEND_SERVICE_ARN" \
  --source-configuration "ImageRepository={ImageIdentifier=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPOSITORY:$GITHUB_SHA,ImageRepositoryType=ECR,ImageConfiguration={Port=8000}}"
```

- [ ] **Step 7: Smoke test backend**

Poll:

```bash
curl -fsS "$PRODUCTION_BACKEND_URL/health"
```

Expected: HTTP 200 before frontend build/deploy starts.

- [ ] **Step 8: Build frontend after backend URL is known**

Build frontend with production backend URL:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL="$PRODUCTION_BACKEND_URL" \
  --build-arg API_INTERNAL_URL="$PRODUCTION_BACKEND_URL" \
  -t "$ECR_FRONTEND_REPOSITORY:$GITHUB_SHA" ./frontend
```

- [ ] **Step 9: Update frontend App Runner and smoke test**

Deploy frontend image and verify:

```bash
curl -fsS "$PRODUCTION_FRONTEND_URL/api/health"
```

Expected: HTTP 200.

- [ ] **Step 10: Verify no old providers remain**

Run:

```bash
rg -n "Vercel|Railway|Supabase|VERCEL|RAILWAY|SUPABASE" .github/workflows/deploy.yml
```

Expected: no output.

- [ ] **Step 11: Commit**

```bash
git add .github/workflows/deploy.yml deploy/AWS_CICD_GUIDE.md deploy/ENVIRONMENT_MATRIX.md
git commit -m "ci: replace production deploy with aws app runner"
```

---

### Task 4: Define RDS Private Migration and Bootstrap Path

**Files:**
- Modify: `deploy/MANUAL_DEPLOY_STEPS.md`
- Modify: `deploy/DEPLOYMENT_PLAN.md`
- Optional Create: `scripts/aws_migrate.sh`

- [ ] **Step 1: Choose the approved execution environment**

Record one migration path in `deploy/MANUAL_DEPLOY_STEPS.md`:

```markdown
Migrations must run from an environment that can reach the private RDS endpoint:

- Preferred v1: AWS CloudShell or bastion/admin host with VPC access.
- Alternative: temporary one-off App Runner-compatible admin task after explicit approval.
- Not allowed: public RDS exposure for convenience.
```

- [ ] **Step 2: Require snapshot before migration**

Add this command block:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier a20-postgres-prod \
  --db-snapshot-identifier a20-postgres-prod-before-migration-$(date +%Y%m%d%H%M%S)
```

- [ ] **Step 3: Document migration command**

Add:

```bash
DATABASE_URL="postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB" \
uv run alembic upgrade head
```

- [ ] **Step 4: Document bootstrap command boundary**

Add:

```bash
ASSET_STORAGE_PROVIDER=s3 \
AWS_S3_BUCKET=a20-course-assets-prod \
AWS_S3_PREFIX=courses \
uv run python -m scripts.bootstrap_course_data
```

If the actual bootstrap entrypoint differs, update this step to the exact existing command before execution.

- [ ] **Step 5: Verify**

Run:

```bash
rg -n "private RDS|create-db-snapshot|alembic upgrade head|ASSET_STORAGE_PROVIDER=s3" deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md
```

Expected: migration access, snapshot, migration, and bootstrap boundaries are explicit.

- [ ] **Step 6: Commit**

```bash
git add deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md
git commit -m "docs: define private rds migration path"
```

---

### Task 5: Correct Frontend Build and Domain Cutover Sequencing

**Files:**
- Modify: `deploy/MANUAL_DEPLOY_STEPS.md`
- Modify: `deploy/DEPLOYMENT_PLAN.md`
- Modify: `deploy/ENVIRONMENT_MATRIX.md`

- [ ] **Step 1: Mark initial frontend build as optional**

In manual deploy steps, clarify:

```markdown
The frontend image may be built once with the backend App Runner default URL for temporary-domain smoke testing. It must be rebuilt after `api.<domain>` is attached because `NEXT_PUBLIC_API_URL` is baked into the Next.js build.
```

- [ ] **Step 2: Add explicit rebuild after custom API domain**

Add:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.<domain> \
  --build-arg API_INTERNAL_URL=https://api.<domain> \
  -t a20-frontend:"$COMMIT_SHA-domain" ./frontend
```

- [ ] **Step 3: Add browser console gate**

Ensure smoke test includes:

```markdown
- [ ] Browser network tab shows no calls to localhost, Railway, Vercel, or old backend URLs.
- [ ] Frontend static bundle references `https://api.<domain>` after final cutover.
```

- [ ] **Step 4: Verify**

Run:

```bash
rg -n "baked|rebuild|api.<domain>|localhost|Railway|Vercel" deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md deploy/ENVIRONMENT_MATRIX.md
```

Expected: final API URL rebuild requirement is documented.

- [ ] **Step 5: Commit**

```bash
git add deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md deploy/ENVIRONMENT_MATRIX.md
git commit -m "docs: correct frontend production build sequencing"
```

---

### Task 6: Lock Asset Delivery Cutover Checks

**Files:**
- Modify: `deploy/PRODUCTION_CHECKLIST.md`
- Modify: `deploy/MANUAL_DEPLOY_STEPS.md`
- Modify: `deploy/DEPLOYMENT_PLAN.md`

- [ ] **Step 1: Add S3 object parity gate**

Add:

```markdown
- [ ] Every DB asset key used by course/lecture APIs exists under `s3://a20-course-assets-prod/courses/`.
- [ ] Missing S3 object count is zero.
- [ ] No production API response returns local absolute filesystem paths.
```

- [ ] **Step 2: Add CloudFront range request verification**

Add:

```bash
curl -I -H "Range: bytes=0-1023" "https://<cloudfront-domain>/courses/<representative-video>.mp4"
```

Expected:

```text
HTTP 206 Partial Content
```

- [ ] **Step 3: Add backend non-proxy gate**

Add:

```markdown
- [ ] Video URLs are CloudFront URLs generated by backend metadata responses.
- [ ] FastAPI does not stream large MP4 bytes to browsers.
```

- [ ] **Step 4: Verify**

Run:

```bash
rg -n "HTTP 206|Partial Content|missing S3|CloudFront URLs|does not stream" deploy/PRODUCTION_CHECKLIST.md deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md
```

Expected: asset parity and range request gates are present.

- [ ] **Step 5: Commit**

```bash
git add deploy/PRODUCTION_CHECKLIST.md deploy/MANUAL_DEPLOY_STEPS.md deploy/DEPLOYMENT_PLAN.md
git commit -m "docs: add asset delivery cutover gates"
```

---

### Task 7: Final Predeploy Verification

**Files:**
- Modify: `deploy/PRODUCTION_CHECKLIST.md`

- [ ] **Step 1: Run static mismatch checks**

Run:

```bash
rg -n "Vercel|Railway|Supabase|VERCEL|RAILWAY|SUPABASE" .github/workflows deploy
```

Expected: old providers appear only in historical/mismatch documentation, not in active workflow instructions.

- [ ] **Step 2: Run workflow config checks**

Run:

```bash
rg -n "workflow_call|id-token: write|configure-aws-credentials|apprunner update-service|docker build" .github/workflows
```

Expected: CI is reusable and deploy workflow uses AWS OIDC plus App Runner updates.

- [ ] **Step 3: Run Docker port checks**

Run:

```bash
rg -n "\\$\\{PORT:-8000\\}|PORT=3000|server.js|0.0.0.0" Dockerfile frontend/Dockerfile
```

Expected: backend and frontend can bind App Runner runtime ports.

- [ ] **Step 4: Run local tests**

Run:

```bash
uv run pytest tests/test_docker_compose_healthcheck.py -q
npm test -- --run tests/unit/app-metadata.test.ts
```

Expected: pass, or blockers are documented in `deploy/PRODUCTION_CHECKLIST.md`.

- [ ] **Step 5: Mark checklist**

Update `deploy/PRODUCTION_CHECKLIST.md` only for verified items. Do not mark AWS resources complete until they exist.

- [ ] **Step 6: Commit**

```bash
git add deploy/PRODUCTION_CHECKLIST.md
git commit -m "docs: record predeploy verification status"
```

---

## Execution Order

1. Task 1: freeze deploy mismatch.
2. Task 2: make CI reusable and Python 3.12 aligned.
3. Task 3: replace deploy workflow with AWS App Runner.
4. Task 4: define private RDS migration/bootstrap path.
5. Task 5: correct frontend build/domain sequencing.
6. Task 6: lock asset cutover checks.
7. Task 7: run final predeploy verification.

Do not create AWS production resources until Tasks 1-7 are complete.

## Self-Review

- Spec coverage: covers all known blockers from review: old deploy providers, missing `workflow_call`, Python 3.11 mismatch, frontend build timing, private RDS migration path, asset delivery verification, and final predeploy checks.
- Placeholder scan: no `TBD` or unspecified placeholder tasks remain. Angle-bracket values represent user/environment-specific deploy values, not implementation gaps.
- Type consistency: workflow variables use names already documented in `deploy/ENVIRONMENT_MATRIX.md`.
