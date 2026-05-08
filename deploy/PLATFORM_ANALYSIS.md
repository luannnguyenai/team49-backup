# Platform Analysis - AWS-First Deployment Options

**Date:** 2026-05-08
**Stack:** FastAPI, PostgreSQL/pgvector, Redis/Valkey, Next.js
**Data:** about 15 GB course/video assets
**Priority:** learn AWS while keeping the first GitHub-triggered production
deploy simple.

## Decision

Use AWS simple managed architecture for v1:

```text
Amplify Hosting + App Runner + RDS + ElastiCache + S3 + CloudFront + Terraform
```

Keep ECR + GitHub OIDC app deployment as a later hardening step after v1 is
working.

## Why This Option Wins For V1

- Amplify gives the frontend a managed GitHub auto-deploy path.
- App Runner gives the backend a managed container runtime with source auto
  deploy.
- RDS, ElastiCache, VPC, NAT, S3, CloudFront, Route 53, ACM, CloudWatch, and
  Secrets Manager still provide real AWS learning value.
- Terraform gives repeatable infrastructure changes without making the first app
  deploy depend on a custom pipeline.
- S3 + CloudFront is the correct path for course/video delivery.

## Option Comparison

| Option | Fit | CI/CD simplicity | AWS learning value | Main drawback |
|---|---|---|---|---|
| AWS simple managed: Amplify + App Runner | Recommended v1 | High | High | Requires explicit VPC egress design |
| App Runner + ECR + GitHub OIDC | Later hardening | Medium | Very high | Too much before first deploy |
| ECS Fargate + ALB | Later if needed | Medium | Very high | More networking and operations |
| Hybrid Vercel/Render/Railway + AWS assets | Fastest launch | Very high | Low-medium | Does not satisfy AWS-first goal |
| EKS | Not v1 | Low | High | Operationally excessive |

## Recommended Architecture

```text
GitHub
  -> CI gate
  -> Amplify Hosting for Next.js
  -> App Runner for FastAPI

App Runner
  -> private RDS PostgreSQL + pgvector
  -> private ElastiCache Redis/Valkey
  -> NAT Gateway for LLM/email egress when required

Browser
  -> CloudFront
  -> private S3 bucket
```

Custom domains:

```text
app.<domain> -> Amplify
api.<domain> -> App Runner
cdn.<domain> -> CloudFront
```

## Key Risk: App Runner VPC Egress

The backend needs private access to RDS/ElastiCache and may need public outbound
access to LLM/email providers. When App Runner uses a VPC connector for private
resources, public egress must be designed explicitly.

Recommended production default:

- Keep RDS and ElastiCache private.
- Attach App Runner VPC connector.
- Use NAT Gateway if tutor/email calls must work in production.
- Monitor NAT spend from day one.

If NAT is deferred, production tutor/email traffic is not fully validated.

## Cost Estimate

| Cost item | Demo/light | Small prod |
|---|---:|---:|
| Amplify Hosting | $2-20 | $10-50 |
| App Runner backend | $15-35 | $35-90 |
| RDS PostgreSQL | $18-35 | $35-80 |
| ElastiCache | $12-20 | $20-45 |
| S3 15 GB | <$1 | <$1 |
| CloudFront data out | $5-20 | $20-90 |
| Secrets Manager | $1-5 | $3-10 |
| CloudWatch | $2-10 | $10-30 |
| Route 53 hosted zone | ~$1 | ~$1 |
| NAT Gateway, if used | $35-80+ | $35-120+ |
| Total without NAT | $56-147/month | $134-397/month |
| Total with NAT | $91-227/month | $169-517/month |

This excludes taxes, support plan, domain registration, and LLM provider usage.

## Upgrade Path

Start with:

```text
Amplify + App Runner source auto deploy + Terraform-managed infrastructure
```

Upgrade to:

```text
GitHub Actions -> AWS OIDC -> ECR SHA image -> App Runner update
```

Move to ECS Fargate only when App Runner limits are real:

- Background workers are required.
- More deployment strategy control is required.
- Private networking requirements exceed App Runner fit.
- Sidecars or service discovery are needed.
