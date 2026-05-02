# Deployment Plan

## Goal

Deploy the current AI Adaptive Learning Platform to a stable production environment with:
- public frontend access
- protected backend API access
- persistent PostgreSQL and Redis
- repeatable deployment and rollback steps

## Current Product Shape

The repository already supports a containerized production-oriented runtime:
- FastAPI backend on port `8000`
- Next.js frontend on port `3000`
- PostgreSQL 16
- Redis 7
- `docker-compose.yml` plus `docker-compose.prod.yml`

This means the lowest-risk first production path is not a platform rewrite. It is a controlled Docker Compose deployment on a Linux host.

## Recommended Deployment Strategy

### Phase 1: Production MVP Infrastructure

Use one Linux VM as the application host:
- OS: Ubuntu 24.04 LTS
- Reverse proxy: Nginx or Caddy
- Containers: Docker Engine + Docker Compose v2
- App services: `frontend`, `backend`
- Data services:
  - preferred: managed PostgreSQL + managed Redis
  - acceptable first step: self-hosted PostgreSQL + Redis on the same VM, but only if budget or setup speed is the priority

Minimum VM sizing for the first production release:
- `4 vCPU / 8 GB RAM / 80 GB SSD` for app containers plus light production traffic
- `8 vCPU / 16 GB RAM / 160 GB SSD` if PostgreSQL and Redis also run on the same VM
- keep at least `20-30 GB` free disk headroom for image pulls, logs, and DB growth

This app is not doing model inference locally, so LLM cost is external. The main local resource pressure comes from:
- Next.js production build memory
- FastAPI workers
- PostgreSQL buffers and connections
- local course assets under `data/courses/`

Recommended public topology:

```text
Internet
  -> HTTPS reverse proxy
  -> Next.js frontend container
  -> FastAPI backend container
  -> PostgreSQL
  -> Redis
```

### Why this is the best first deployment

- Matches the repo's existing Dockerfiles and compose files.
- Keeps operations simple while the product is still changing quickly.
- Avoids premature split across Vercel, Railway, Render, and separate networking rules.
- Makes debugging easier because app behavior stays close to local development.

## Database Platform Constraint: pgvector

This repo is not plain PostgreSQL-only by contract:
- `docker-compose.yml` uses `pgvector/pgvector:pg16`
- Alembic migrations create the `vector` extension

That means any managed PostgreSQL target must support `pgvector` or `CREATE EXTENSION vector`.

Before choosing a DB provider, verify:
- extension support exists on the target plan and region
- the app role can use the extension or the provider pre-enables it
- backup and restore keep extension compatibility

Safe examples to evaluate first:
- Supabase PostgreSQL with pgvector support
- managed PostgreSQL providers that explicitly document `pgvector`

Do not choose a managed PostgreSQL service first and “figure out vector later”. That is a deployment blocker.

## Recommended Domains

- `app.<your-domain>` for frontend
- `api.<your-domain>` for backend

Examples:
- `https://app.example.com`
- `https://api.example.com`

Set frontend runtime/build config so browser requests go to the public API domain, not `localhost`.

## Production Environment Design

### Frontend

- Build from `frontend/Dockerfile` runner target.
- Expose only through reverse proxy.
- Set `NEXT_PUBLIC_API_URL=https://api.<your-domain>`.
- Frontend already exposes `/api/health` for container and proxy health probes.

### Backend

- Run with the production command already defined in `docker-compose.prod.yml`.
- Keep backend container private behind the reverse proxy when possible.
- Expose `/health` to internal checks and proxy health checks.
- Set `CORS_ORIGINS` explicitly to the production frontend origin, for example `["https://app.example.com"]`.

### Database

Preferred:
- managed PostgreSQL with backups, point-in-time recovery, and TLS

Fallback:
- self-hosted PostgreSQL with:
  - persistent volume
  - daily backups
  - host firewall
  - no public inbound access except from the app host if absolutely required

### Redis

Preferred:
- managed Redis

Fallback:
- self-hosted Redis with password, private network only, and append-only persistence

### Object and Course Assets

The repo currently expects course assets under `data/courses/<course>/`.

Short term:
- mount the asset directory into the backend host/container
- use an explicit release asset path on the host, for example `/srv/ai-learning/data/courses`
- sync staging and production assets from the same approved source, not from ad-hoc developer machines

Long term:
- move binary assets to object storage such as S3-compatible storage
- keep only metadata and references in the app/database

Recommended asset sync policy:
- transcripts, slides, JSON artifacts: store in Git or a controlled artifact bundle
- large video files: sync from object storage or a controlled rsync source
- production and staging should each have their own asset manifests so missing files are detectable before release

## Production Readiness Gaps To Close

These are the main gaps before a serious public launch:

1. Secrets management
- `.env` handling is still file-centric.
- Move production secrets to the host secret store, CI/CD secrets, or a vault solution.

2. Reverse proxy and TLS
- The repo does not yet include Nginx/Caddy production config.
- Add TLS termination, compression, secure headers, and request size limits.

3. Backups
- Automated PostgreSQL backup and restore drill are not documented in repo yet.

4. Observability
- Logs exist, but production monitoring and alerting are not yet defined.
- Add container log shipping, uptime checks, and error alerting.
- Lowest-friction stack recommendation: Grafana + Loki for logs, plus Uptime Kuma or external uptime probes.

5. Deployment automation
- There is no complete production release workflow yet.
- First deployment can be manual; later move to GitHub Actions or another CI/CD runner.

6. Data import runbook
- Canonical import and product shell import are documented, but production sequencing should be formalized.

7. Abuse protection
- LLM-backed endpoints can create direct usage cost.
- Add reverse-proxy request size limits, basic rate limiting, and stricter limits on auth and tutor-heavy endpoints.

8. Secret rotation policy
- `SECRET_KEY` rotation is not free because JWT sessions will be invalidated.
- Plan for explicit maintenance windows or dual-key support before frequent rotation.

## Rollout Phases

### Phase 0: Hardening Before First Deploy

- Confirm `.env` production values.
- Generate a strong `SECRET_KEY`.
- Choose one LLM provider and verify quota/billing.
- Decide where PostgreSQL and Redis will live.
- Verify the chosen PostgreSQL target supports `pgvector`.
- Verify CORS and public API URL behavior.
- Verify health endpoints.
- Test `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` on a clean machine.

### Phase 1: First Staging Environment

Create a staging environment that mirrors production:
- separate domain or subdomain
- separate database
- separate Redis
- same container images and env structure

Run in staging:
- database migration
- canonical content import
- product shell import
- parity checks
- frontend smoke test
- backend API smoke test
- auth/login smoke test
- quiz / assessment / tutor smoke test

### Phase 2: First Production Deployment

Deploy in this order:

1. Provision host and DNS
2. Configure reverse proxy and TLS
3. Provision database and Redis
4. Copy production env file or inject secrets
5. Pull repo or deployment artifact
6. Build and start containers in production mode
7. Run migrations
8. Run canonical import and product shell import if production DB is empty
9. Run parity validation
10. Run application smoke checks
11. Open access to users

### Phase 3: Stabilization

After first production release:
- add daily backup automation
- add log aggregation
- add uptime monitoring
- add deployment pipeline with branch or tag promotion
- add rollback drill

## Concrete Deployment Runbook

### Server setup

Install on the Linux host:
- Docker Engine
- Docker Compose v2
- Nginx or Caddy
- Git

Recommended host layout:
- app root: `/srv/ai-learning/app`
- env file: `/srv/ai-learning/shared/.env.production`
- backups: `/srv/ai-learning/backups`
- runtime assets: `/srv/ai-learning/data/courses`

Open only:
- `80/tcp`
- `443/tcp`
- optional `22/tcp` for SSH with key auth only

Close public access to:
- PostgreSQL
- Redis
- raw backend port
- raw frontend port

### Application deploy sequence

From the repo root:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m src.scripts.pipeline.import_canonical_artifacts_to_db
docker compose exec backend uv run python -m src.scripts.pipeline.import_product_shell_to_db
docker compose exec backend uv run python -m src.scripts.pipeline.check_canonical_runtime_parity
```

Then verify:
- frontend home page loads
- backend `/health` returns `200`
- frontend `/api/health` returns `200`
- login/register flow works
- one course page loads
- one learning-unit page loads
- one quiz session can start and submit

## Reverse Proxy Baseline

The minimum reverse proxy configuration should provide:
- HTTPS with automatic certificate renewal
- redirect `http -> https`
- `app.<domain>` -> frontend on `127.0.0.1:3000`
- `api.<domain>` -> backend on `127.0.0.1:8000`
- gzip or zstd compression
- request body size limit
- per-IP rate limiting on auth and API paths

This deploy folder now includes a `Caddyfile` baseline for that setup.

## Rollback Strategy

### Application rollback

- keep the previous image version or previous git revision on the server
- redeploy the previous known-good version
- do not run destructive data cleanup as part of rollback

### Database rollback

- prefer forward-fix over schema rollback unless the migration was proven bad
- take backup snapshots before production migrations
- use restore only for severe data corruption or unrecoverable release failure

## Migration Safety Policy

For production releases, treat schema changes as two-step changes whenever possible:

1. backward-compatible migration
- add nullable columns, additive indexes, new tables, or new code paths first

2. application rollout
- deploy code that can work with both old and new shapes during the transition

3. cleanup migration later
- remove deprecated columns or constraints only after the new code is stable

Avoid same-release destructive schema changes unless the app is in a planned maintenance window and rollback has been tested.

This matters even on a single VM because container restarts can still surface startup-time migration failures.

## CI/CD Recommendation

Do this after manual deployment is stable.

Minimum pipeline:
- backend tests
- frontend type-check
- frontend tests
- build backend image
- build frontend image
- optional staging deploy on merge to `main`
- manual approval before production deploy

## Suggested Next Deliverables For This Repo

Create these next:
- `deploy/nginx.conf` if the team prefers Nginx over Caddy
- GitHub Actions workflow for staging deploy
- GitHub Actions workflow for production deploy with manual approval

## Decision Summary

Recommended now:
- one Linux VM
- Docker Compose production mode
- reverse proxy with TLS
- managed PostgreSQL and Redis if budget allows
- manual first deployment, automated later
- explicit `pgvector` support check before choosing the DB provider

Not recommended for the first release:
- splitting frontend and backend across unrelated hosting platforms
- exposing database or Redis publicly
- introducing Kubernetes before traffic and team size justify it
