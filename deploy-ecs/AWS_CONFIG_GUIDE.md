# AWS Config Guide — ECS

## Networking

- Public subnets for `ALB` (2 AZs)
- Private subnets for `ECS tasks`, `RDS`, and `ElastiCache` (2 AZs)
- **`NAT Gateway` is required for v1**: Fargate tasks in private subnets cannot
  pull from `ECR`, fetch from `Secrets Manager`, or write to `CloudWatch Logs`
  without egress. Without it, every task fails to start with
  `ResourceInitializationError`. (See `HOW_TO_FIX.md` trap B1.)
- Cost mitigation later: replace NAT with VPC interface endpoints
  (`ecr.api`, `ecr.dkr`, `logs`, `secretsmanager`) plus the S3 Gateway endpoint.
- Separate security groups, with chained ingress only:
  - `alb-sg`: ingress 80/443 from world
  - `frontend-sg`: ingress 3000 from `alb-sg`
  - `backend-sg`: ingress 8000 from `alb-sg`
  - `db-sg`: ingress 5432 from `backend-sg`
  - `redis-sg`: ingress 6379 from `backend-sg`

## ECS

- One cluster for production v1
- Separate task definitions for frontend and backend
- **Separate task execution role and task role** — execution role pulls from
  ECR / reads Secrets Manager / writes logs; task role is what runtime code
  uses (e.g. S3). Merging them widens privilege silently (trap B5).
- **CloudWatch log group must exist before service apply** (trap B7). Create
  log groups in Terraform, not via `awslogs-create-group`.
- **Secrets via task definition `secrets[]`** bound to Secrets Manager ARNs,
  never via `environment[]` (trap B4).
- **Migrations run as a separate one-off task** (`a20-backend-migrate`) using
  the same image and secrets, not as the long-running service start command
  (trap A4).
- ALB target group health checks:
  - backend: `/health`, interval 15s, timeout 5s, healthy 2, unhealthy 3
  - frontend: `/api/health`, interval 15s, timeout 5s, healthy 2
- Service health-check grace period: backend ≥ 60s, frontend ≥ 120s. Next.js
  standalone cold start is ~90s in practice (trap B2).
- Container port consistency: same number in Dockerfile `EXPOSE`, task def
  `containerPort`, and target group `port` (trap B3). Backend 8000, frontend 3000.
- Deploy success gate is **not** `services-stable` alone. It is
  `services-stable` AND target group healthy host count > 0 AND HTTP 200 on
  `/health` AND HTTP 200 on a DB-backed route (trap B6, A5).

## Data Layer

- RDS PostgreSQL in private subnets
- **`deletion_protection = true`** on the instance. Disable explicitly before
  any teardown (trap A6). Documented in `MANUAL_DEPLOY_STEPS.md` section 11.
- Storage encrypted with KMS, automated backups 7 days
- `pgvector` enabled after provisioning (one-time DDL, not Terraform)
- ElastiCache in private subnets
- Secrets Manager holds connection strings and secret material; backend task
  execution role gets `secretsmanager:GetSecretValue` scoped to the backend
  secret ARN only.
- Production passwords containing `%` must work end-to-end. `alembic/env.py`
  escapes `%` -> `%%` before assigning to configparser (trap A3). Verify by
  running the migration task with a `%`-bearing password.

## Assets

- Private S3 bucket with versioning and encryption
- CloudFront uses OAC
- Optional signed URLs only if hotlink protection is needed

## Domains

- `app.<domain>` -> ALB frontend rule
- `api.<domain>` -> ALB backend rule
- `cdn.<domain>` -> CloudFront

## Observability

- CloudWatch log groups with retention
- ECS CPU/memory alarms
- ALB 5xx or unhealthy host alarms
- RDS CPU/storage alarms
- Budget thresholds at low, medium, high spend
