# AWS CI/CD Guide - Native Auto Deploy First

Production v1 uses AWS-native app deploys:

- Amplify Hosting auto deploys the Next.js frontend from GitHub.
- App Runner auto deploys the FastAPI backend from GitHub/source.
- GitHub Actions is a CI validation gate, not the v1 app deploy engine.

Terraform is the exception: infrastructure `plan/apply` may use GitHub Actions
OIDC because it manages infrastructure drift, not per-commit app releases.

## Required Cleanup Before V1

The repository contains a legacy workflow that deploys to Vercel, Railway, and
Supabase. Before the AWS production path is used:

- `push main` must not deploy to Vercel/Railway/Supabase.
- CI must still run before production merges.
- AWS app deploys must remain Amplify/App Runner native auto deploy in v1.

Acceptable cleanup:

- Disable the `push main` trigger.
- Replace the workflow with a manual/no-op reference.
- Delete it after confirming the old stack is retired.

## V1 Workflow Model

```text
pull_request to main
  -> GitHub Actions CI
       backend lint/test
       frontend lint/type-check/build/test

merge or push to production branch
  -> Amplify detects commit and deploys frontend
  -> App Runner detects commit and deploys backend
```

Native auto deploy means AWS rebuilds/redeploys from the configured GitHub
branch. It is not local hot reload and it does not replace CI branch protection.

## GitHub Branch Policy

Branch policy:

- Protect `main`.
- Require CI checks before merge.
- Use pull requests for production changes.
- Deploy only from `main` or the explicitly selected production branch.

## Application CI Requirements

CI should run:

- Python 3.12.
- Backend ruff lint and format check.
- Backend pytest with Postgres and Redis services.
- Node 20.
- Frontend lint.
- Frontend type-check.
- Frontend production build.
- Frontend unit tests where available.

CI should not store production AWS app deploy credentials for v1.

## Terraform Infrastructure CI

Terraform CI is separate from app CI/CD.

```text
pull_request touching deploy/terraform
  -> terraform fmt
  -> terraform validate
  -> terraform plan

workflow_dispatch apply=true
  -> recreate backend.hcl and terraform.tfvars from protected values
  -> terraform plan
  -> terraform apply reviewed plan
```

Required GitHub Environment values:

| Name | Type | Purpose |
|---|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | secret | IAM role assumed by GitHub Actions through OIDC |
| `TF_BACKEND_HCL_PROD` | secret or protected variable | Full `deploy/terraform/live/prod/backend.hcl` content |
| `TFVARS_PROD` | secret or protected variable | Full `deploy/terraform/live/prod/terraform.tfvars` content |

The workflow must write `backend.hcl` and `terraform.tfvars` at runtime because
real versions are not committed:

```yaml
- name: Write backend config
  working-directory: deploy/terraform/live/prod
  run: printf '%s' "${{ secrets.TF_BACKEND_HCL_PROD }}" > backend.hcl

- name: Write production variables
  working-directory: deploy/terraform/live/prod
  run: printf '%s' "${{ secrets.TFVARS_PROD }}" > terraform.tfvars
```

If the team does not want Terraform variables in GitHub Environment values,
run Terraform locally from an approved admin machine instead.

## Amplify Auto Deploy

Required settings:

| Setting | Value |
|---|---|
| App name | `a20-frontend` |
| Repository | this GitHub repo |
| Branch | `main` or selected production branch |
| App root | `frontend` |
| Install command | `npm ci --legacy-peer-deps` |
| Build command | `npm run build` |
| Env | `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL`, `NEXT_TELEMETRY_DISABLED`, `NODE_ENV` |
| Auto deploy | enabled |

Smoke test:

```bash
curl --fail "https://<frontend-amplify-url>/api/health"
```

Changing `NEXT_PUBLIC_API_URL` requires a new frontend build.

## App Runner Auto Deploy

Required settings:

| Setting | Value |
|---|---|
| Service name | `a20-backend` |
| Repository | this GitHub repo |
| Branch | `main` or selected production branch |
| Source | root `Dockerfile` |
| Port | `8000` or runtime `PORT` |
| Health path | `/health` |
| VPC connector | attached when RDS/ElastiCache are private |
| Auto deploy | enabled |

Smoke test:

```bash
curl --fail "https://<backend-app-runner-url>/health"
```

## Deployment Ordering

For normal code changes:

1. Open PR.
2. CI passes.
3. Merge to production branch.
4. Amplify/App Runner auto deploy independently.
5. Smoke test the changed surface.

For DB migration changes:

1. Merge only after CI passes.
2. Let App Runner deploy backend code.
3. Confirm an RDS snapshot exists.
4. Run `alembic upgrade head` from a trusted admin environment.
5. Smoke test backend.
6. Trigger or wait for Amplify rebuild if frontend env/API behavior changed.

If this ordering becomes too manual, that is the trigger to evaluate the optional
ECR/OIDC deploy workflow.

## Rollback

Frontend:

- Redeploy a previous successful Amplify build, or revert the commit and let
  Amplify redeploy.

Backend:

- Redeploy a previous App Runner deployment if available, or revert the commit
  and let App Runner redeploy.

Database:

- Restore from an RDS snapshot into a new instance, validate it, then repoint
  `DATABASE_URL`.

Assets:

- Restore S3 object versions and invalidate CloudFront paths if needed.

## Optional Later: ECR + GitHub OIDC App Deploy

Upgrade when you need:

- Immutable Docker image digest rollback.
- GitHub Environment approval gates for production app deploys.
- One workflow that builds, pushes, updates App Runner, waits, and smoke-tests.

Later workflow:

```text
push main or workflow_dispatch
  -> CI gate
  -> assume AWS deploy role through OIDC
  -> build backend image
  -> push SHA tag to ECR
  -> update App Runner backend service
  -> wait for operation completion
  -> smoke test backend
```

Use least-privilege OIDC roles and short-lived credentials. Do not introduce
long-lived AWS access keys for app deploy.
