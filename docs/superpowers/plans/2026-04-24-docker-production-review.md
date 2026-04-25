# Docker Production Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Docker build time and image size, clarify the role of each service for production VPS deployment, and harden the backend/frontend container setup so production deploys are predictable, fast, and maintainable.

**Architecture:** Keep the current `backend + frontend + postgres + redis` compose topology for now, but separate dev and prod concerns more aggressively. Treat backend image construction, asset delivery, and Redis usage as independent architecture decisions instead of letting the current local-dev compose shape leak into production.

**Tech Stack:** Docker, Docker Compose, Python 3.12, FastAPI, SQLAlchemy, uv, Next.js 14, Node 20 Alpine, PostgreSQL, Redis

---

## Current Findings

- Backend Docker build context is the repo root and the root `Dockerfile` uses `COPY . .`, so production builds currently pull in much more than the runtime actually needs.
- Root `.dockerignore` is not excluding nested course assets recursively, so `data/courses/**` media is very likely being sent into build context.
- The largest cost driver is repository asset volume, not Redis. Current local data includes roughly `11.24 GB` of `.mp4` under `data/courses/`.
- Backend image doubles as both application image and asset carrier because the API serves `/data/...` from local disk.
- Redis is used for login rate limiting and token denylist/revocation, but not for general caching, background jobs, or queues.
- Redis is currently a soft dependency: app startup tolerates Redis failure, and token guard behavior is fail-open when Redis is unavailable.
- Backend default container command is not production-self-sufficient; it depends on Compose command override to start `uvicorn`.
- Frontend Docker setup is healthier than backend, but still lacks explicit dependency caching strategy for faster rebuilds.

## Baseline Convention

- The original plan assumed a pure pre-change baseline.
- Execution has been intentionally adjusted so the first measured build baseline is taken after the minimal safety patch that recursively ignores `.mp4` files.
- This keeps the first real Docker build practical while still preserving a narrow change scope.
- All later comparisons should treat this as the `post-mp4-ignore baseline`, not as an untouched historical baseline.

---

## Safety Rules

- Make one Docker concern change at a time. Do not combine `.dockerignore`, backend startup, Redis semantics, and asset strategy into one rollout.
- Every risky change must have a before/after verification step and a rollback path.
- Prefer reversible config changes before structural image changes.
- Do not remove local asset access from production flow until replacement storage or mounting strategy is proven.
- Do not tighten Redis failure behavior until production Redis availability and startup expectations are explicit.
- Do not claim a Docker optimization is successful until build time, image size, and runtime behavior are all rechecked.

## Rollout Order

1. Apply the minimal safety patch that recursively ignores `.mp4` files.
2. Measure the first practical `post-mp4-ignore baseline`.
3. Rebuild and verify nothing runtime-critical disappeared.
4. Make backend image runnable safely without changing asset strategy yet.
5. Add dependency caching improvements.
6. Decide asset strategy explicitly.
7. Revisit Redis production behavior last.

## Stop Conditions

- Stop if backend build succeeds but app import or healthcheck fails.
- Stop if `/data/...` routes break while production still depends on local assets.
- Stop if Compose prod starts only because of an override and the image itself is no longer self-consistent.
- Stop if a `.dockerignore` change removes migration, config, or runtime bootstrap files.
- Stop if Redis hardening changes cause auth startup or login flow regressions before an outage policy is agreed.

## Rollback Guidance

- Keep each Docker-related edit in a separate commit or isolated patch set.
- Save pre-change baseline metrics before the first edit.
- After each phase, retain the last known-good image tag or git state until the next phase passes verification.
- If a risky phase fails verification, revert only that phase and continue from the last passing state.

---

## Execution Log

### Phase 1: Baseline Measurement

**Status:** `partial`

**Scope Note**

- This phase now measures the first baseline after the minimal `.dockerignore` `.mp4` patch.
- Additional `.dockerignore`, startup, asset, or Redis changes remain out of scope for this phase.

**Checklist**

- [ ] Capture backend cold build time.
- [x] Capture backend warm build time.
- [x] Capture frontend cold build time.
- [x] Capture frontend warm build time.
- [x] Capture image sizes and large layers.
- [x] Save findings in this document.

**Verification**

- [x] Only the minimal `.mp4` ignore safety patch was applied before baseline capture.
- [x] Baseline numbers are written down and reproducible enough to compare later.

**Evidence**

- Result: `partial`
- Notes: `Backend warm build = 21.54s on 2026-04-25. Frontend cold build = 144.86s. Frontend warm build = 6.94s. Backend image reported by docker images = 1.63GB; frontend image reported by docker images = 1.44GB. Backend image inspect size = 484,642,153 bytes. Frontend image inspect size = 372,844,363 bytes. Backend largest layers: uv sync 618MB, COPY . . 325MB, uv binary copy 58.5MB, apt layer 45MB, base image 85.3MB. Frontend largest layers: npm ci 917MB, node/alpine layer 130MB. Backend cold build was started on 2026-04-24 after the mp4 patch but user interrupted the command after about 309s; the image was produced, but the exact completed cold timing was not captured cleanly.`

### Phase 2: Minimal `.dockerignore` Reduction

**Status:** `completed`

**Checklist**

- [x] Change only recursive ignore rules needed to cut obvious large assets.
- [x] Avoid mixing startup or Redis changes into this phase.
- [x] Rebuild backend after the ignore change.
- [x] Establish the new `post-mp4-ignore baseline` for later comparisons.

**Verification**

- [x] Backend build still succeeds.
- [x] Required app files still exist in image context.
- [x] No runtime-critical file disappeared accidentally.

**Evidence**

- Result: `pass`
- Notes: `Root .dockerignore was patched from a shallow mp4 rule to recursive rules: *.mp4 and **/*.mp4. Backend image was rebuilt successfully. Container verification showed MP4_COUNT=0 under /app. App import succeeded with docker run --rm ai-adaptive-learning-backend:latest uv run python -c "import src.api.app". A plain python import failed with ModuleNotFoundError: fastapi, which confirms the current image contract depends on uv-managed runtime rather than global site-packages; this is a Phase 3 image-contract concern, not a Phase 2 regression.`

### Phase 3: Backend Image Startup Contract

**Status:** `completed`

**Checklist**

- [x] Make backend image runnable from its own default command.
- [x] Keep dev-only reload behavior out of production contract.
- [x] Verify migration/startup assumptions explicitly.

**Verification**

- [x] Image starts without depending on Compose override to hide a broken default command.
- [x] App import/health path still works.

**Evidence**

- Result: `pass`
- Notes: `Dockerfile CMD was changed from uv run python src/api/app.py to uv run python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000. Backend rebuild after this change took 26.09s. Standalone image verification passed on 2026-04-25: docker run with the default command served /health successfully and returned HEALTH_STATUS=200 without relying on a Compose command override. Backend inspect size after the change = 484,650,619 bytes.`

### Phase 4: Dependency Cache Optimization

**Status:** `completed`

**Checklist**

- [x] Add caching changes only after image contract is stable.
- [x] Measure cold vs warm rebuild impact separately.
- [x] Keep behavior identical while optimizing build speed.

**Verification**

- [x] Cold build still passes.
- [x] Warm build is faster than baseline.
- [x] Dependency resolution remains stable.

**Evidence**

- Result: `pass`
- Notes: `Added # syntax=docker/dockerfile:1.7 to both Dockerfiles. Backend now uses RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --no-dev. Frontend now uses RUN --mount=type=cache,target=/root/.npm npm ci --legacy-peer-deps, and the empty apk add layer was removed. Post-patch rebuilds on 2026-04-25: backend rebuild = 117.04s, frontend rebuild = 124.66s. Immediate warm rebuilds after that: backend = 3.78s, frontend = 2.35s. This is materially faster than the earlier warm baselines (backend 21.54s, frontend 6.94s), though the exact improvement should be treated as a combined effect of Docker layer cache plus the new cache mounts rather than a cache-mount-only benchmark. No runtime behavior changes were introduced in this phase.`

### Phase 5: Asset Delivery Decision

**Status:** `pending`

**Checklist**

- [ ] Decide whether production serves local `/data/...` assets.
- [ ] Choose volume, pre-provisioned storage, or external/object storage.
- [ ] Avoid removing local assets before replacement path is verified.

**Verification**

- [ ] Production asset path is tested.
- [ ] Backend image no longer carries accidental heavy media.

**Evidence**

- Result: `pending`
- Notes: `pending`

### Phase 6: Redis Production Decision

**Status:** `pending`

**Checklist**

- [ ] Confirm Redis call sites and security impact.
- [ ] Decide whether Redis stays optional or becomes required.
- [ ] Verify auth behavior after any Redis policy change.

**Verification**

- [ ] Production Redis behavior is documented.
- [ ] Outage semantics are tested or intentionally accepted.

**Evidence**

- Result: `pending`
- Notes: `pending`

---

## Review Scope

### In Scope

- Root `Dockerfile`
- `frontend/Dockerfile`
- Root `.dockerignore`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- Backend runtime assumptions tied to `src/api/app.py`
- Redis responsibility and production necessity
- Build-time size, cacheability, and deploy flow to VPS

### Out of Scope

- Full Kubernetes migration
- CI provider selection details beyond image build/push strategy
- Rewriting backend storage layer in the same pass

---

## Phase Plan

### Task 1: Establish A Measured Baseline

**Goal:** Stop guessing. Capture the current cost of the existing Docker setup before changing anything.

**Files to Inspect**

- `Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`

- [ ] Measure cold backend build time.
- [ ] Measure warm backend build time.
- [ ] Measure cold frontend build time.
- [ ] Measure warm frontend build time.
- [ ] Record current image sizes with `docker images`.
- [ ] Record large backend layers with `docker history`.
- [ ] Record effective build context size and top offenders.
- [ ] Save the baseline numbers in this document or a sibling ops note before making fixes.
- [ ] Do not edit Docker-related files before the baseline is written down.

**Success Criteria**

- We have a before/after benchmark for build time and image size.
- We know whether the dominant bottleneck is context upload, dependency install, or asset copy.

### Task 2: Fix Backend Build Context And `.dockerignore`

**Goal:** Prevent large non-runtime assets from entering the backend image build unless explicitly intended.

**Files**

- Modify: `.dockerignore`
- Inspect: `Dockerfile`
- Inspect: `docker-compose.yml`
- Inspect: `docker-compose.prod.yml`

- [ ] Replace shallow patterns like `data/*.mp4` with recursive exclusions that cover nested assets.
- [ ] Exclude `data/courses/**` from default backend build context unless production explicitly requires local asset serving.
- [ ] Review whether `.venv`, local caches, notebooks, logs, exports, docs, and generated artifacts are fully excluded.
- [ ] Verify the new ignore rules do not accidentally hide files required by backend runtime or migrations.
- [ ] Apply ignore rule changes in the smallest possible patch first.
- [ ] Rebuild after ignore changes and compare context transfer/build duration.
- [ ] Verify backend image still contains required app code, migrations, and config.
- [ ] Verify runtime behavior before moving to the next task.

**Success Criteria**

- Backend build no longer ingests multi-GB course media by default.
- Context transfer time drops materially on both local machine and VPS-class environments.

### Task 3: Separate Dev And Prod Backend Image Behavior

**Goal:** Make backend container behavior explicit instead of relying on Compose overrides to compensate for a generic image.

**Files**

- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`

- [ ] Decide whether to keep one multi-stage Dockerfile or split dev/prod Dockerfiles.
- [ ] Make the production backend image runnable standalone with a correct default server command.
- [ ] Keep reload/dev-only behavior in dev compose rather than in the image contract.
- [ ] Ensure Alembic migration execution strategy is intentional for production startup.
- [ ] Remove unnecessary dev assumptions from the production image path.
- [ ] Change startup contract only after `.dockerignore` work is verified stable.
- [ ] Verify container boot via image default command, not only via Compose override.
- [ ] Verify health/import path after startup command changes before touching any other runtime concern.

**Success Criteria**

- Production image can run correctly outside Compose command overrides.
- Dev and prod startup behavior are intentionally different, not accidentally coupled.

### Task 4: Rework Dependency Caching And Image Reproducibility

**Goal:** Improve rebuild speed and make the image more deterministic.

**Files**

- Modify: `Dockerfile`
- Modify: `frontend/Dockerfile`
- Inspect: `pyproject.toml`
- Inspect: `frontend/package-lock.json`

- [ ] Pin `uv` source/version instead of using floating `latest`.
- [ ] Add BuildKit cache mounts or equivalent caching strategy for Python dependency resolution/install.
- [ ] Add cache-aware strategy for `npm ci` in frontend build.
- [ ] Confirm dependency files are copied before source code to preserve layer cache value.
- [ ] Check whether backend runtime dependencies can be trimmed or split if ML/data packages are not needed in the API image.
- [ ] Introduce cache changes without changing app behavior in the same patch.
- [ ] Verify cold and warm rebuild deltas separately.

**Success Criteria**

- Warm rebuilds are significantly faster.
- Image creation is more reproducible across machines and over time.

### Task 5: Decide The Production Asset Strategy

**Goal:** Stop mixing application runtime concerns with heavy binary course content unless that coupling is truly intended.

**Files**

- Inspect: `src/api/app.py`
- Inspect: `docker-compose.prod.yml`
- Inspect: deployment assumptions around `data/`

- [ ] Decide whether backend should serve local `data/` assets in production at all.
- [ ] If yes, choose between bind-mounted volume and pre-provisioned server storage instead of baking assets into image.
- [ ] If no, define replacement path: object storage, CDN, or external file server.
- [ ] Confirm which subset of `data/` is bootstrap/import-only and which subset is runtime-critical.
- [ ] Update the production deployment model to match that decision.
- [ ] Do not remove asset files from runtime path until the replacement path is tested.
- [ ] Verify `/data/...` behavior explicitly if production still relies on it.

**Success Criteria**

- Backend image contains app code and required runtime dependencies, not a large media archive by accident.
- Asset delivery path is explicit and production-appropriate.

### Task 6: Reassess Redis As A Production Dependency

**Goal:** Decide whether Redis stays, and if it stays, whether it should remain soft-fail.

**Files**

- Inspect: `src/api/app.py`
- Inspect: `src/redis_client.py`
- Inspect: `src/middleware/rate_limit.py`
- Inspect: `src/services/token_guard.py`
- Inspect: auth router/service paths touching token revoke or rate limit

- [ ] Confirm all current Redis call sites.
- [ ] Classify each usage as security-critical, performance-related, or optional.
- [ ] Decide whether logout/token revocation and login throttling must fail closed in production.
- [ ] If Redis remains optional, document the exact degraded-security behavior.
- [ ] If Redis becomes required, tighten health checks and startup semantics accordingly.
- [ ] Do not change Redis failure policy in the same patch as Docker build optimization.
- [ ] Verify login, logout, and token refresh behavior after any Redis-related production decision.

**Success Criteria**

- Redis is either justified and hardened, or removed cleanly from production scope.
- Production operators know exactly what breaks if Redis is unavailable.

### Task 7: Harden The VPS Deployment Path

**Goal:** Optimize for production deploy experience, not just local developer convenience.

**Files**

- Modify: `docker-compose.prod.yml`
- Inspect: deployment scripts or docs if present

- [ ] Decide whether production images are built on VPS or built in CI and pushed to a registry.
- [ ] Prefer `build once, pull many` if VPS CPU/network budget is limited.
- [ ] Review healthcheck, restart policy, env handling, and secret injection.
- [ ] Review reverse proxy/TLS expectations if production traffic terminates outside the app containers.
- [ ] Document the intended deploy flow in a short ops note.
- [ ] Keep one known-good deployment method available while evaluating the new one.

**Success Criteria**

- VPS deploy path is predictable and low-friction.
- Production updates do not depend on slow full-source builds on the target server unless explicitly chosen.

---

## Verification Gates

### Gate 1: After Baseline

- [ ] Baseline numbers are saved.
- [ ] No Docker files changed yet.

### Gate 2: After `.dockerignore` Changes

- [ ] `docker compose build backend` still succeeds.
- [ ] Backend image still includes required source and migration files.
- [ ] App import or health endpoint still works.
- [ ] No asset-dependent route broke unintentionally.

### Gate 3: After Backend Startup Changes

- [ ] Backend image runs correctly from its own default command.
- [ ] Prod compose override is no longer masking a broken image contract.
- [ ] Migration/startup sequence is still valid.

### Gate 4: After Cache Optimizations

- [ ] Cold build still succeeds.
- [ ] Warm build is measurably faster.
- [ ] No dependency resolution regression appears.

### Gate 5: After Asset Strategy Decision

- [ ] Production asset path is tested.
- [ ] Backend no longer carries heavy media accidentally.
- [ ] Runtime behavior matches the chosen asset design.

### Gate 6: After Redis Decision

- [ ] Redis role in production is documented.
- [ ] Auth behavior under Redis outage is tested or explicitly accepted.
- [ ] Security behavior is no longer accidental.

---

## Review Checklist

### A. Baseline And Evidence

- [ ] Record backend cold build time.
- [ ] Record backend warm build time.
- [ ] Record frontend cold build time.
- [ ] Record frontend warm build time.
- [ ] Record backend image size.
- [ ] Record frontend image size.
- [ ] Record top 5 largest backend layers.
- [ ] Record top 5 largest directories in repo relevant to build context.

### B. Backend Dockerfile

- [ ] `Dockerfile` has a valid production default command.
- [ ] Dependency install layers are cache-friendly.
- [ ] Source copy happens after dependency metadata copy.
- [ ] No accidental `COPY . .` of multi-GB assets remains without justification.
- [ ] Tool versions are pinned sufficiently for reproducible builds.
- [ ] Final image contains only runtime-critical files.

### C. Frontend Dockerfile

- [ ] Multi-stage build remains intact.
- [ ] `npm ci` path is cache-aware.
- [ ] Final runner image contains only standalone output and runtime deps.
- [ ] No unnecessary packages or no-op commands remain.

### D. `.dockerignore`

- [ ] Recursive media exclusions are correct.
- [ ] Local virtualenv and cache directories are excluded.
- [ ] Test outputs, logs, notebooks, docs, and exports are excluded if not needed at runtime.
- [ ] Ignore rules do not hide migration or config files needed in production.

### E. Compose Topology

- [ ] Dev compose is optimized for iteration.
- [ ] Prod compose is optimized for predictable startup.
- [ ] Production backend does not depend on dev-only bind mounts.
- [ ] Service dependencies and health assumptions are explicit.
- [ ] Restart policies are appropriate for production.

### F. Redis Decision

- [ ] Redis usage list is complete.
- [ ] Redis value is worth the operational overhead.
- [ ] Security behavior under Redis outage is documented.
- [ ] Final decision is one of: keep and harden, keep as optional, or remove.

### G. Asset Strategy

- [ ] `data/courses/**` is not baked into app image by accident.
- [ ] Bootstrap data and runtime assets are distinguished clearly.
- [ ] Production file serving path is documented.
- [ ] VPS disk usage implications are understood before rollout.

### H. Deploy Strategy

- [ ] Registry-based deploy path is evaluated.
- [ ] On-server build path is evaluated and either accepted or rejected intentionally.
- [ ] Rollback path is documented.
- [ ] Build/pull/restart steps are simple enough for repeatable production operations.

### I. Safety And Rollback

- [ ] Each risky Docker change is isolated from unrelated changes.
- [ ] Each phase has a verification result written down.
- [ ] Each phase can be reverted independently.
- [ ] A last known-good image or git state is retained until the next phase passes.
- [ ] No high-risk production assumption changed without explicit validation.

---

## Immediate Must-Fix Candidates

- [ ] Fix root `.dockerignore` so nested course media is excluded from backend build context.
- [ ] Make backend production image runnable without Compose command override.
- [ ] Decide whether production backend image should contain any `data/courses` payload at all.
- [ ] Decide whether Redis outage should weaken auth security behavior in production.
- [ ] Capture baseline build metrics before broader Docker refactor begins.

---

## Notes For Execution

- Start with measurement, then context reduction, then image contract cleanup.
- Do not optimize layer minutiae before fixing the oversized build context.
- Do not move to VPS rollout until asset strategy and Redis behavior are explicit.
- Treat `.dockerignore`, backend startup, asset delivery, and Redis policy as four separate decision tracks.
- When in doubt, prefer the smaller, reversible Docker change first.
