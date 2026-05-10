# Production Checklist — Full AWS ECS

Tick this while executing `DEPLOYMENT_PLAN.md`. Items marked **[L]** are
lessons carried forward from the App Runner postmortem in
[`HOW_TO_FIX.md`](HOW_TO_FIX.md) — they are non-negotiable.

## Pre-deploy

- [ ] Backend `Dockerfile` binds `0.0.0.0:8000` and exposes 8000 **[L: B3]**
- [ ] Frontend `frontend/Dockerfile` `CMD` forces `HOSTNAME=0.0.0.0` **[L: A2]**
- [ ] `.dockerignore` excludes `.dvc/`, `.git/`, `node_modules/`, `frontend/` **[L: A1]**
- [ ] `alembic/env.py` escapes `%` -> `%%` before setting `sqlalchemy.url` **[L: A3]**
- [ ] AWS account quotas verified for ECS, ALB, NAT, ECR, RDS, ElastiCache, S3, CloudFront, Route 53, ACM, Secrets Manager, CloudWatch
- [ ] Region selected: `ap-southeast-1`
- [ ] Domain layout: `app.<domain>`, `api.<domain>`, `cdn.<domain>`
- [ ] Budget thresholds selected (low/medium/high)

## CI/CD

- [ ] GitHub Actions deploy role exists and uses AWS OIDC
- [ ] Trust policy restricts repo + production branch/environment
- [ ] Build uses immutable SHA tags only (no `latest`)
- [ ] Workflow renders task definition JSON from a committed template
- [ ] Workflow runs `aws ecs update-service --force-new-deployment`
- [ ] Deploy gate = `services-stable` **AND** target group healthy **AND** HTTP 200 smoke **[L: B6]**
- [ ] Smoke pack includes a DB-backed route, not only `/health` **[L: A5]**

## Network and ingress

- [ ] VPC exists with DNS support and DNS hostnames enabled
- [ ] 2 public subnets across AZs for ALB
- [ ] 2 private subnets across AZs for ECS, RDS, ElastiCache
- [ ] **NAT Gateway in 1 public subnet, private route table directs `0.0.0.0/0` -> NAT** **[L: B1]**
- [ ] ALB internet-facing
- [ ] Frontend and backend target groups exist with correct port + path
- [ ] Security groups follow least-privilege (`alb-sg` -> `frontend-sg`/`backend-sg` -> `db-sg`/`redis-sg`)

## ECS

- [ ] ECS cluster `a20-prod-cluster` exists with Container Insights on
- [ ] CloudWatch log groups created **before** services **[L: B7]**
- [ ] Backend task definition: port 8000, secrets via `secrets[]` (never `environment`) **[L: B4]**
- [ ] Frontend task definition: port 3000, includes `HOSTNAME=0.0.0.0` env **[L: A2]**
- [ ] Task **execution** role distinct from task role **[L: B5]**
- [ ] Backend service grace period ≥ 60s
- [ ] Frontend service grace period ≥ 120s **[L: B2]**
- [ ] Migration task `a20-backend-migrate` registered with `command=["alembic","upgrade","head"]` **[L: A4]**
- [ ] Service start commands do **not** invoke alembic **[L: A4]**
- [ ] Desired count and autoscaling boundaries recorded

## Data and assets

- [ ] RDS PostgreSQL exists with `deletion_protection = true` **[L: A6]**
- [ ] `pgvector` enabled
- [ ] ElastiCache exists
- [ ] S3 bucket exists, fully private, versioned, TLS-only policy
- [ ] CloudFront distribution exists with OAC
- [ ] Course assets uploaded
- [ ] Video seek (range request) verified through CloudFront

## Application runtime

- [ ] Backend env/secrets complete, secrets sourced from Secrets Manager
- [ ] Frontend env complete (`NEXT_PUBLIC_API_URL` baked at build time) **[L: B8]**
- [ ] `DATABASE_URL` and `REDIS_URL` come from secret sources, not literals
- [ ] Backend `/health` returns 200 through ALB
- [ ] Backend DB-backed route (e.g. `/api/course-sections`) returns 200 **[L: A5]**
- [ ] Frontend `/api/health` returns 200 through ALB
- [ ] CloudFront serves a known asset

## Final cutover

- [ ] Route 53 records created for `app`, `api`, `cdn`
- [ ] ACM certs issued in `ap-southeast-1` (ALB) and `us-east-1` (CloudFront) and attached
- [ ] **Frontend rebuilt and redeployed with production `NEXT_PUBLIC_API_URL`** **[L: B8]**
- [ ] Final smoke pack rerun on `https://app.<domain>` and `https://api.<domain>`

## Cost and rollback

- [ ] Budget alerts enabled
- [ ] ECS/ALB/RDS/CloudFront alarms enabled
- [ ] Deployed image digests recorded
- [ ] Current task definition revisions recorded
- [ ] Rollback path documented (re-point service to previous task def revision)
- [ ] **Teardown runbook requires disabling RDS `deletion_protection` first** **[L: A6]**
- [ ] Teardown runbook disables CloudFront distribution before delete
- [ ] Teardown runbook empties S3 versions before bucket delete
