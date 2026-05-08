# Platform Analysis — AWS Deployment Options

**Date:** 2026-05-07  
**Stack:** FastAPI + PostgreSQL/pgvector + Redis/Valkey + Next.js  
**Data:** ~15 GB MP4 course/video assets  
**Constraint:** Production deployment must be full AWS

---

## TL;DR

Use **AWS App Runner + ECR + RDS PostgreSQL + ElastiCache + S3 + CloudFront** for the first production deployment.

Reasoning:

- It keeps compute, database, cache, storage, CDN, secrets, DNS, TLS, and CI/CD target inside AWS.
- It avoids cross-cloud data paths for video delivery.
- It is simpler than ECS for an initial production deployment.
- It still leaves a clean upgrade path to ECS Fargate or EKS later.

---

## Workload Characteristics

| Area | Current expectation |
|---|---|
| Web traffic | Light to moderate demo/early production usage |
| Video assets | ~15 GB MP4 files, bandwidth-sensitive |
| Backend | FastAPI, SQLAlchemy async, LLM calls, auth, course APIs |
| Frontend | Next.js app deployed as container |
| Database | PostgreSQL with `vector` extension |
| Cache | Redis-compatible runtime for rate limits/session/cache |
| Cost risk | CloudFront data out, App Runner active CPU, RDS size |

The main cost driver is user video watch traffic, not S3 storage size.

---

## Recommended Architecture

```text
                         Route 53 + ACM
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
 app.<domain>           api.<domain>           cdn.<domain>
       │                      │                      │
       ▼                      ▼                      ▼
 App Runner              App Runner             CloudFront
 Next.js                 FastAPI                S3 origin access control
                              │                      │
                              ▼                      ▼
                       Private AWS network       Private S3 bucket
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
        RDS PostgreSQL                 ElastiCache
        + pgvector                     Redis OSS / Valkey
```

Use GitHub Actions with AWS OIDC for CI/CD:

```text
GitHub Actions -> AWS OIDC role -> ECR image push -> App Runner service update
```

---

## AWS Option Comparison

| Option | Fit | Monthly estimate | Use when |
|---|---|---:|---|
| **App Runner** | Recommended v1 | $65-135 demo, $145-380 small prod | You want full AWS with low operational overhead |
| **ECS Fargate + ALB** | More control | $100-450+ | You need fine-grained networking, sidecars, workers, or custom scaling |
| **Lightsail Containers + AWS managed data** | Lower ops/cost but less standard | $40-150+ | You want a simpler AWS product and accept fewer production controls |
| **EKS** | Overkill for v1 | $250+ before workload | You already have Kubernetes operations maturity |

Recommendation: start with App Runner, then move to ECS Fargate only when App Runner constraints become real.

---

## Service Decisions

| Need | Chosen service | Rationale |
|---|---|---|
| Backend compute | App Runner | Container deploy, managed HTTPS, simple scaling |
| Frontend compute | App Runner | Keeps frontend production runtime in AWS |
| Container registry | ECR | Native App Runner image source |
| Database | RDS PostgreSQL | Managed backups, standard Postgres, pgvector support |
| Cache | ElastiCache Redis OSS/Valkey | Managed Redis-compatible runtime |
| Object storage | S3 Standard | Private object store for course/video assets |
| CDN | CloudFront | Edge delivery, range requests, signed URLs if needed |
| Secrets | Secrets Manager | Runtime secret storage and rotation path |
| DNS | Route 53 | Native custom-domain flow |
| TLS | ACM | Integrated public certificates |
| CI/CD auth | AWS OIDC IAM role | Short-lived credentials, no static AWS keys |
| Logs/metrics | CloudWatch | Native App Runner/RDS/CloudFront visibility |

---

## Cost Estimate

Assumptions:

- Region: `ap-southeast-1`.
- One production environment.
- App Runner backend: `1 vCPU / 2 GB`.
- App Runner frontend: `0.5 vCPU / 1 GB`.
- RDS: Single-AZ `db.t4g.micro` or `db.t4g.small`, 20 GB storage.
- ElastiCache: one small node.
- Assets: 15 GB S3 Standard.
- CloudFront data out: 50-200 GB/month for early traffic.

| Cost item | Demo/light | Small prod |
|---|---:|---:|
| App Runner backend | $15-25 | $35-75 |
| App Runner frontend | $8-18 | $20-45 |
| RDS PostgreSQL | $18-35 | $35-80 |
| ElastiCache | $12-20 | $20-45 |
| S3 15 GB | <$1 | <$1 |
| CloudFront data out | $5-20 | $20-90 |
| ECR | <$2 | <$5 |
| Secrets Manager | $2-5 | $5-10 |
| CloudWatch | $2-10 | $10-30 |
| Route 53 hosted zone | ~$1 | ~$1 |
| ACM public certs | $0 | $0 |
| CI/CD | $0-10 | $0-30 |
| **Total** | **$65-135/month** | **$145-380/month** |

This excludes taxes, support plan, domain registration, and LLM provider usage.

---

## Cost Controls

- Configure AWS Budgets before production traffic.
- Alert on CloudFront `BytesDownloaded`.
- Bound App Runner max instances until real traffic is known.
- Set CloudWatch log retention to 7-14 days initially.
- Enable ECR lifecycle policies.
- Enable S3 lifecycle rules for obsolete assets.
- Review Cost Explorer weekly during the first month.

---

## Upgrade Path

Start:

```text
App Runner + RDS + ElastiCache + S3 + CloudFront
```

Move to ECS Fargate if any of these become blockers:

- Need background workers colocated with backend release lifecycle.
- Need advanced service discovery or internal routing.
- Need more control over sidecars, CPU/memory, scaling, or deployment strategy.
- Need private-only ingress behind an ALB.

Move to EKS only if the team already needs Kubernetes for multiple services and has operational maturity for it.

---

## Decision

Use **full AWS App Runner architecture** for v1 production deployment. Keep the deployment plan and every file in `deploy/` aligned to that target.
