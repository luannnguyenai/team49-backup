# AWS Architecture — ECS Managed V1

This diagram set matches `DEPLOYMENT_PLAN.md`.

## Runtime Architecture

```mermaid
flowchart TB
  Dev[Developer] --> GitHub[GitHub Repository]

  GitHub --> CI[GitHub Actions CI]
  GitHub --> Deploy[GitHub Actions Deploy]
  Deploy --> ECR[ECR backend/frontend images]
  Deploy --> ECS[ECS cluster on Fargate]

  User[Browser] --> Route53[Route 53 DNS]
  Route53 --> ALB[Application Load Balancer]
  Route53 --> CloudFront[CloudFront CDN]

  ALB --> FE[ECS service: frontend]
  ALB --> BE[ECS service: backend]

  BE --> Secrets[Secrets Manager]
  BE --> RDS[(RDS PostgreSQL + pgvector)]
  BE --> Redis[(ElastiCache Redis/Valkey)]

  CloudFront --> OAC[Origin Access Control]
  OAC --> S3[(Private S3 bucket)]

  FE -->|API calls| ALB
  BE --> NAT[NAT Gateway]
  NAT --> Providers[LLM / Email providers]
```

## Deploy Flow

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant GH as GitHub
  participant CI as GitHub Actions CI
  participant CD as GitHub Actions Deploy
  participant ECR as Amazon ECR
  participant ECS as Amazon ECS
  participant ALB as Application Load Balancer

  Dev->>GH: Merge to main
  GH->>CI: Run lint, tests, build
  CI-->>GH: Required checks pass
  GH->>CD: Trigger deploy workflow
  CD->>ECR: Build and push images
  CD->>ECS: Register task definition revisions
  CD->>ECS: Update backend/frontend services
  ECS->>ALB: Replace tasks through rolling deployment
  CD->>ALB: Smoke test frontend/backend paths
```

## Responsibility Split

| Component | Responsibility |
|---|---|
| GitHub Actions CI | Validate code before deploy |
| GitHub Actions Deploy | Build, push, rollout, smoke |
| Terraform | Provision reviewed infrastructure |
| ECR | Private image registry |
| ECS cluster | Shared compute control plane |
| ECS services | Frontend/backend runtime |
| ALB | Public ingress and health-based traffic routing |
| RDS | Authoritative application data |
| ElastiCache | Cache/session/rate limit store |
| S3 | Private asset storage |
| CloudFront | Browser asset and video delivery |
| Secrets Manager | Runtime secrets |
| CloudWatch / Budgets | Logs, alarms, cost controls |

## Boundary Notes

- Terraform manages infrastructure, not app releases.
- ECS service rollout uses new task definition revisions, not mutable containers.
- Frontend and backend stay separate services even when sharing one cluster.
- Course videos must stream `CloudFront -> Browser`, not through FastAPI.
