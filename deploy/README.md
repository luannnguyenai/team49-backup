# Deploy Folder - AWS-First Simple Managed

This folder contains the production deployment plan for the A20 app. The current
target is an AWS-first, managed-services deployment that is simple enough for a
first production launch and still useful for learning real AWS operations.

## Source Of Truth

Use the documents in this order:

1. `DEPLOYMENT_PLAN.md` - authoritative phase plan and gates.
2. `TERRAFORM_PLAN.md` - implementation plan for AWS infrastructure as code.
3. `ENVIRONMENT_MATRIX.md` - runtime variables, secrets, and CI values.
4. `MANUAL_DEPLOY_STEPS.md` - operator runbook for executing the plan.
5. `PRODUCTION_CHECKLIST.md` - final go/no-go checklist.

The remaining files explain decisions or give focused references:

- `PLATFORM_ANALYSIS.md` - why the selected AWS architecture is the v1 target.
- `AWS_ARCHITECTURE.md` - runtime and deploy-flow diagrams.
- `AWS_CONFIG_GUIDE.md` - service-specific AWS configuration notes.
- `AWS_CICD_GUIDE.md` - CI/CD model and GitHub Actions boundaries.

## V1 Decision Lock

| Area | Decision |
|---|---|
| Frontend | AWS Amplify Hosting, GitHub branch auto deploy |
| Backend | AWS App Runner, repository Dockerfile/source auto deploy |
| Database | RDS PostgreSQL with `vector` extension |
| Cache | ElastiCache Redis OSS or Valkey |
| Course assets | Private S3 bucket, uploaded outside Terraform |
| Asset delivery | CloudFront with S3 Origin Access Control |
| DNS/TLS | Route 53 + ACM after temporary-domain smoke tests |
| Secrets | Secrets Manager plus service env/secret references |
| Logs/metrics | CloudWatch, AWS Budgets, focused alarms |
| App CI/CD v1 | GitHub Actions is a CI gate only; deploys are native AWS auto deploy |
| Infra management | Terraform remote S3 state and reviewed `plan/apply` |
| Later hardening | ECR + GitHub OIDC + custom deploy workflow after v1 is stable |

## Terraform Boundary

Terraform should manage AWS infrastructure after the remote-state bootstrap:

- VPC, subnets, route tables, security groups, NAT if accepted.
- S3 bucket security settings, CloudFront distribution, OAC.
- RDS, ElastiCache, App Runner service shell, Amplify app/branch when the GitHub
  connection approach is approved.
- Route 53, ACM, CloudWatch alarms, Budgets.
- Secrets Manager secret containers, not secret values.

Terraform should not manage:

- Real secret values.
- GitHub OAuth authorization handshakes.
- 15 GB course/video object uploads.
- Alembic migrations, `pgvector` SQL execution, or bootstrap/import data jobs.
- Per-commit app deployments; Amplify/App Runner native auto deploy handles those.

## Mandatory Gates Before Production

- Disable or replace the legacy `.github/workflows/deploy.yml` so `push main`
  cannot deploy to Vercel, Railway, or Supabase.
- Bootstrap Terraform state and review the first production `terraform plan`.
- Choose the App Runner egress model before private RDS/Redis are connected.
  Recommended production default: private RDS/Redis plus NAT Gateway when
  tutor/email providers must be reachable.
- Decide the GitHub connection path for App Runner and Amplify:
  - Preferred: authorize/import connection-managed resources, then manage stable
    infrastructure in Terraform.
  - Alternative: use provider access tokens only after accepting their Terraform
    state implications.
- Smoke test temporary AWS domains before attaching custom domains.

## Non-Goals For V1

- No custom ECR/OIDC application deploy workflow until native AWS auto deploy is
  stable.
- No ECS, EKS, Kubernetes, multi-region HA, or DRM.
- No FastAPI proxying of large video files. Course videos must stream directly
  from CloudFront to the browser.
