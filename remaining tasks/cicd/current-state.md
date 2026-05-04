# CI/CD Current State

Date: 2026-05-03

## Scope

This note captures the current CI/CD state as implemented in the repository today, based on:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/kg-sync.yml`
- `deploy/README.md`
- `deploy/DEPLOYMENT_PLAN.md`
- `README.md`

## Active GitHub Actions Workflows

### 1. `CI`

File: `.github/workflows/ci.yml`

Trigger:

- `push` to all branches except `main`
- `pull_request` targeting `main`

Concurrency:

- `group: ci-${{ github.ref }}`
- cancels in-progress runs on the same branch / PR

Jobs:

1. `lint-backend`
   - runner: `ubuntu-latest`
   - installs Python 3.11
   - installs `ruff`
   - runs:
     - `ruff check src/ scripts/`
     - `ruff format --check src/ scripts/`

2. `test-backend`
   - depends on `lint-backend`
   - runner: `ubuntu-latest`
   - provisions service containers:
     - `postgres:16-alpine`
     - `redis:7-alpine`
   - sets test env:
     - `DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test_ai_learning`
     - `REDIS_URL=redis://localhost:6379/0`
     - auth settings for JWT
   - installs `requirements.txt`
   - runs:
     - `alembic upgrade head`
     - `pytest tests/ -v --tb=short --junitxml=reports/junit.xml --cov=src --cov-report=xml:reports/coverage.xml`
   - uploads `reports/` as artifact

3. `lint-frontend`
   - runner: `ubuntu-latest`
   - working directory: `frontend`
   - installs Node 20
   - runs:
     - `npm ci --legacy-peer-deps`
     - `npm run lint`

4. `typecheck-frontend`
   - depends on `lint-frontend`
   - runner: `ubuntu-latest`
   - working directory: `frontend`
   - installs Node 20
   - runs:
     - `npm ci --legacy-peer-deps`
     - `npx tsc --noEmit`
     - `npm run build`
   - sets:
     - `NEXT_PUBLIC_API_URL=http://localhost:8000`

Summary:

- This workflow is the main validation gate for backend lint/tests and frontend lint/typecheck/build.
- It does not run frontend unit tests or Playwright e2e tests.

### 2. `Deploy`

File: `.github/workflows/deploy.yml`

Trigger:

- `push` to `main`

Concurrency:

- `group: deploy-production`
- does not cancel an in-progress deploy

Jobs:

1. `ci-gate`
   - intended to reuse `./.github/workflows/ci.yml` before deployment

2. `migrate-db`
   - depends on `ci-gate`
   - installs Python 3.11
   - installs `requirements.txt`
   - runs:
     - `alembic upgrade head`
   - uses:
     - `DATABASE_URL=${{ secrets.SUPABASE_DB_URL }}`

3. `deploy-backend`
   - depends on `migrate-db`
   - installs Railway CLI
   - deploys backend with:
     - `railway up --service "${{ secrets.RAILWAY_SERVICE_ID }}" --detach`
   - polls Railway deployment status until `ACTIVE`
   - smoke tests:
     - `GET ${{ secrets.NEXT_PUBLIC_API_URL }}/health`

4. `deploy-frontend`
   - depends on `deploy-backend`
   - working directory: `frontend`
   - installs Node 20
   - installs dependencies
   - installs Vercel CLI
   - runs:
     - `vercel pull --yes --environment=production`
     - `vercel build --prod`
     - `vercel deploy --prebuilt --prod`
   - smoke tests deployed frontend URL with `curl`

5. `summary`
   - always runs after backend/frontend deploy jobs complete
   - writes a deployment table to `GITHUB_STEP_SUMMARY`

Summary:

- Current workflow assumes:
  - database hosted on Supabase
  - backend hosted on Railway
  - frontend hosted on Vercel

### 3. `KG Sync`

File: `.github/workflows/kg-sync.yml`

Trigger:

- `push` to `main` only when these paths change:
  - `data/kg_bridges.yaml`
  - `src/kg/**`
  - `alembic/versions/*kg*`

Jobs:

1. `kg-sync`
   - runner: `ubuntu-latest`
   - provisions `postgres:16`
   - uses `uv`
   - installs Python 3.12
   - runs:
     - `uv sync --extra dev`
     - `uv run alembic upgrade head`
     - `uv run pytest tests/kg`
     - `uv run python -m src.scripts.build_kg --dry-run`

Summary:

- This is a targeted verification workflow for knowledge-graph-related changes.
- It is separate from the main CI workflow.

## Current Deployment Topology in Actions

As implemented in `.github/workflows/deploy.yml`, production deployment is split across three providers:

- Frontend: Vercel
- Backend: Railway
- Database: Supabase PostgreSQL

This is the currently encoded GitHub Actions deployment topology.

## Current Runtime Architecture in App Code

The application code itself is not Supabase-specific.

Observed runtime contract:

- backend reads generic `DATABASE_URL`
- backend uses PostgreSQL via SQLAlchemy async + `asyncpg`
- frontend talks to backend through `API_INTERNAL_URL` or `NEXT_PUBLIC_API_URL`
- Redis is used as a separate runtime dependency

Not observed in current runtime code:

- `@supabase/supabase-js`
- Supabase Auth integration
- Supabase Storage integration in active runtime code
- Supabase-specific environment variables such as:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`

Conclusion:

- Supabase is currently a deployment/database hosting detail in GitHub Actions, not an application platform dependency in the active codebase.

## Mismatches and Risks

### 1. Deploy workflow conflicts with deploy docs

`deploy/README.md` and `deploy/DEPLOYMENT_PLAN.md` describe a Railway-centric demo deployment:

- frontend on Railway
- backend on Railway
- Postgres on Railway plugin
- Redis on Railway plugin

But `.github/workflows/deploy.yml` describes:

- frontend on Vercel
- backend on Railway
- database on Supabase

This is the largest current CI/CD inconsistency in the repo.

### 2. `ci.yml` is referenced as reusable, but is not declared reusable

`deploy.yml` uses:

- `uses: ./.github/workflows/ci.yml`

However, `ci.yml` currently declares:

- `on.push`
- `on.pull_request`

and does not declare:

- `on.workflow_call`

Risk:

- `ci-gate` may not work as intended because `ci.yml` is not currently defined as a reusable workflow.

### 3. CI coverage is incomplete for frontend test layers

Current CI validates:

- backend lint
- backend tests
- frontend lint
- frontend typecheck
- frontend production build

Current CI does not validate:

- frontend `vitest` unit tests
- frontend Playwright e2e tests

### 4. Python versions are inconsistent across workflows

Observed:

- `ci.yml`: Python 3.11
- `deploy.yml`: Python 3.11
- `kg-sync.yml`: Python 3.12
- project runtime target in `pyproject.toml`: `>=3.12`

Risk:

- behavior may differ between KG workflow and main CI/deploy workflow
- CI may miss Python-3.12-specific issues

## Practical Current-State Summary

If the repository is interpreted strictly by what GitHub Actions currently encode:

- feature branches and PRs run CI checks
- `main` triggers a production-style deploy pipeline
- KG-related changes trigger an additional KG workflow on `main`
- deployment strategy in Actions is hybrid:
  - Vercel + Railway + Supabase

If the repository is interpreted by deployment docs and local runtime docs:

- the intended or previously planned demo stack looks more like:
  - Railway + Railway Postgres + Railway Redis

## Recommended Follow-up Decisions

The repo needs one source of truth for CI/CD:

1. Keep the hybrid deploy model:
   - Vercel frontend
   - Railway backend
   - Supabase DB

2. Or align everything to the Railway demo plan:
   - Railway frontend
   - Railway backend
   - Railway Postgres
   - Railway Redis

After that decision, update:

- `.github/workflows/deploy.yml`
- `deploy/README.md`
- `deploy/DEPLOYMENT_PLAN.md`
- any required secrets documentation
