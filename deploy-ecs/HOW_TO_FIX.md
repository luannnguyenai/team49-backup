# ECS Deploy — Lessons Learned and Failure Modes To Prevent

Date: 2026-05-09

This document carries forward the failure modes hit during the App Runner +
Terraform deployment session on `feat-terraform-aws` (see
[`../deploy/HOW_TO_FIX.md`](../deploy/HOW_TO_FIX.md)) and maps each one to the
ECS rollout so we do not repeat them.

It also lists ECS-specific traps that App Runner abstracted away. Read this
before starting any phase in `DEPLOYMENT_PLAN.md`.

---

## A. Failures Carried Forward From App Runner

| # | Failure on App Runner | ECS analogue | Where it must be enforced |
|---|---|---|---|
| 1 | `.dvc/tmp/lock` polluted backend Docker context | Same. ECS still uses Docker build. | Phase 1 DoD: confirm `.dockerignore` ignores `.dvc/` before any `docker build`. |
| 2 | Next.js standalone bound to App Runner-injected `HOSTNAME` | Same. Fargate sets its own env. Next.js standalone reads `process.env.HOSTNAME`. | Phase 2 DoD: `frontend/Dockerfile` `CMD` must force `HOSTNAME=0.0.0.0` at process launch. |
| 3 | Alembic failed on `%` in production DATABASE_URL | Same. Migrations on ECS still use `alembic/env.py` and configparser. | Phase 20 DoD: `alembic/env.py` must keep the `% -> %%` escape. Verify with a URL containing `%`. |
| 4 | App Runner `StartCommand` quoting/working-dir traps | ECS task `command`/`entryPoint` arrays bypass shell, but migration chains still bite. | Phase 20: run migrations as a **separate one-off ECS task** (`aws ecs run-task`), never as the long-running service start command. |
| 5 | `/health` passed but DB-backed route failed (`relation "users" does not exist`) | Same. ALB health check `/health` only proves the process is up, not that schema exists. | Phase 24 DoD: smoke test must include a DB-backed route such as `GET /api/course-sections`. |
| 6 | Terraform destroy blocked by RDS `deletion_protection = true` | Same. Terraform manages RDS the same way. | Phase 27: rollback/teardown runbook must require disabling `deletion_protection` first. |

## B. ECS-Specific Traps That Did Not Exist On App Runner

App Runner hides these. Fargate does not.

### B1. Tasks in private subnets cannot pull images or read secrets without egress

A Fargate task in a private subnet **cannot start** unless one of the following
is true:

- The subnet has a route to a NAT Gateway, or
- VPC Interface Endpoints exist for `ecr.api`, `ecr.dkr`, `s3` (Gateway), `logs`,
  `secretsmanager`, and (if used) `ssm`

Failure mode without it:

```text
ResourceInitializationError: unable to pull secrets or registry auth: ...
CannotPullContainerError: ... no such host
```

Decision for v1: enable a single NAT Gateway in one AZ. Document it in the
network module. If cost pressure rises later, swap to VPC endpoints.

### B2. ALB health check grace period must cover real cold start

App Runner had its own grace-period semantics. ECS has two settings that both
have to be right:

- target group `HealthCheck` `HealthyThresholdCount`, `Interval`, `Timeout`
- ECS service `health_check_grace_period_seconds`

Real measured cold starts in this app:

- backend FastAPI: a few seconds
- frontend Next.js standalone: ~90s in practice on first boot

Recommended starting values:

- backend target group: path `/health`, interval `15`, timeout `5`, healthy threshold `2`
- frontend target group: path `/api/health`, interval `15`, timeout `5`, healthy threshold `2`
- backend service grace period: `60`
- frontend service grace period: `120`

### B3. Container port must match three places exactly

This was already a App Runner trap and gets worse on ECS. The same port number must appear in:

1. `Dockerfile` `EXPOSE`
2. ECS task definition `containerDefinitions[].portMappings[].containerPort`
3. ALB target group `port`

Backend: `8000`. Frontend: `3000`. Do not vary these without changing all three.

### B4. Secrets via task definition `secrets` block, not env

Putting `DATABASE_URL` into `environment` leaks the secret into task
definitions and CloudWatch. Use the task definition `secrets` array bound to
Secrets Manager ARNs. Task **execution** role (not task role) needs
`secretsmanager:GetSecretValue` for those ARNs.

### B5. Two roles, two purposes — do not merge

- `task execution role`: pull from ECR, write CloudWatch logs, read Secrets Manager at task start
- `task role`: what application code uses at runtime (S3, etc.)

Merging them is a common mistake and silently widens privilege.

### B6. Service stability is not deploy success

`aws ecs wait services-stable` returns success when the service settles, even
if every new task is crash-looping back to the previous revision. Always pair
it with:

- target group `unhealthy host count = 0`
- explicit HTTP 200 smoke against the ALB
- a DB-backed smoke route

### B7. CloudWatch log group must exist before task start

Task definitions referencing a `awslogs-group` that does not exist will fail
to start with a non-obvious error. Create log groups in Terraform alongside
the service, do not rely on `awslogs-create-group`.

### B8. Frontend `NEXT_PUBLIC_*` is build-time, not runtime

Same trap as before but worth restating. Changing `NEXT_PUBLIC_API_URL` after
domain cutover requires a **new image build and push**, not just a service
update.

---

## C. Required Pre-Flight Checks Before Each Risky Phase

These map 1:1 to phases in `DEPLOYMENT_PLAN.md`.

### Before Phase 6 (push backend image)

- [ ] `.dockerignore` excludes `.dvc/`, `.git/`, `node_modules/`, `frontend/`
- [ ] Local `docker build` succeeds without DVC noise
- [ ] Backend image listens on `0.0.0.0:8000` when run locally
- [ ] `GET /health` returns `200` from the running container

### Before Phase 7 (push frontend image)

- [ ] `frontend/Dockerfile` `CMD` forces `HOSTNAME=0.0.0.0`
- [ ] `EXPOSE 3000` present
- [ ] Build args `NEXT_PUBLIC_API_URL`, `API_INTERNAL_URL` set to production values, not `localhost`
- [ ] Local container responds `200` on `GET /api/health`

### Before Phase 19 (backend ECS service)

- [ ] CloudWatch log group `/ecs/a20-backend` exists
- [ ] Backend task execution role can `GetSecretValue` on backend secret ARN
- [ ] Backend SG allows egress to RDS SG on `5432` and Redis SG on `6379`
- [ ] Backend task subnets have route to NAT or required VPC endpoints
- [ ] Target group health check path `/health`, healthy threshold ≤ 2
- [ ] Service `health_check_grace_period_seconds` ≥ `60`

### Before Phase 20 (run migrations)

- [ ] Production `DATABASE_URL` available via Secrets Manager
- [ ] `alembic/env.py` still escapes `%` (`% -> %%`)
- [ ] One-off task definition `a20-backend-migrate` registered with `command = ["alembic", "upgrade", "head"]`
- [ ] Migration task uses the **same image, network, secrets** as the service
- [ ] Service is **not** configured to run alembic on every start

### Before Phase 22 (frontend ECS service)

- [ ] Backend service is `RUNNING` and `/health` returns `200` through ALB
- [ ] DB-backed smoke route returns `200`
- [ ] Frontend image rebuilt with the production `NEXT_PUBLIC_API_URL`
- [ ] Frontend target group health path `/api/health`, grace period ≥ `120`

### Before Phase 24 (smoke test)

Smoke pack must include all four:

- [ ] `GET /health` on backend ALB rule -> `200`
- [ ] `GET /api/health` on frontend ALB rule -> `200`
- [ ] DB-backed route (e.g. `GET /api/course-sections`) -> `200`
- [ ] CloudFront asset URL serves a known object

### Before any teardown (Phase 27)

- [ ] `aws rds modify-db-instance --no-deletion-protection --apply-immediately`
- [ ] Final RDS snapshot taken
- [ ] CloudFront distribution disabled before delete (delete fails otherwise)
- [ ] S3 bucket emptied (versioned objects too) before delete

---

## D. Anti-Patterns To Block In Review

- Embedding `alembic upgrade head` in the service container's start command
- Putting secrets in task definition `environment` instead of `secrets`
- Reusing the task execution role as the task role
- Trusting `services-stable` as a deploy gate without ALB target health checks
- Checking only `/health` and declaring deploy successful
- Changing `NEXT_PUBLIC_API_URL` and only restarting the service (no rebuild)
- Hardcoding container ports in only one of Dockerfile / task def / target group
- Provisioning private-subnet Fargate tasks without NAT or VPC endpoints
- Storing AWS access keys in GitHub secrets instead of OIDC
- Marking `deletion_protection = false` permanently to avoid teardown friction

---

## E. Cross-References

- App Runner postmortem: [`../deploy/HOW_TO_FIX.md`](../deploy/HOW_TO_FIX.md)
- Phase plan: [`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md)
- Operator runbook: [`MANUAL_DEPLOY_STEPS.md`](MANUAL_DEPLOY_STEPS.md)
- Final go/no-go: [`PRODUCTION_CHECKLIST.md`](PRODUCTION_CHECKLIST.md)
- Env values: [`ENVIRONMENT_MATRIX.md`](ENVIRONMENT_MATRIX.md)
