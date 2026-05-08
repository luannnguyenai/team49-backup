# AWS Architecture - Simple Managed V1

This diagram set matches `DEPLOYMENT_PLAN.md`.

## Runtime Architecture

```mermaid
flowchart TB
  Dev[Developer] --> GitHub[GitHub Repository]

  GitHub --> CI[GitHub Actions CI<br/>lint / test / build]
  GitHub --> Amplify[AWS Amplify Hosting<br/>Next.js frontend<br/>native auto deploy]
  GitHub --> AppRunner[AWS App Runner<br/>FastAPI backend<br/>source auto deploy]

  User[Browser] --> Route53[Route 53 DNS]
  Route53 --> Amplify
  Route53 --> AppRunner
  Route53 --> CloudFront[CloudFront CDN<br/>cdn.domain]

  Amplify -->|API calls| AppRunner

  AppRunner --> VPCConnector[App Runner VPC Connector]
  VPCConnector --> AppRunnerSG[Backend security group]
  AppRunnerSG --> PrivateSubnets[Private subnets]
  PrivateSubnets --> RDS[(RDS PostgreSQL<br/>pgvector)]
  PrivateSubnets --> Redis[(ElastiCache<br/>Redis OSS / Valkey)]

  AppRunner --> Secrets[Secrets Manager / service secret refs]
  PrivateSubnets --> PrivateRoutes[Private route table]
  PrivateRoutes --> NAT[NAT Gateway<br/>when public egress required]
  NAT --> PublicRoutes[Public route table]
  PublicRoutes --> IGW[Internet Gateway]
  IGW --> Providers[LLM / Email providers]

  CloudFront --> OAC[Origin Access Control]
  OAC --> S3[(Private S3 bucket<br/>course videos / assets)]

  Terraform[Terraform<br/>reviewed plan/apply] --> Network[VPC / subnets / routes / security groups]
  Terraform --> RDS
  Terraform --> Redis
  Terraform --> S3
  Terraform --> CloudFront
  Terraform -. import after first healthy deploy .-> AppRunner
  Terraform -. import after first healthy deploy .-> Amplify
  Terraform --> Route53
  Terraform --> Observability[CloudWatch alarms<br/>Budgets / log retention]
```

## Deploy Flow

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant GH as GitHub
  participant CI as GitHub Actions CI
  participant TF as Terraform
  participant AMP as Amplify
  participant APR as App Runner
  participant AWS as AWS Infrastructure

  Dev->>GH: Open PR
  GH->>CI: Run lint, tests, build
  CI-->>GH: Required checks pass
  Dev->>GH: Merge to production branch

  GH->>AMP: Native frontend auto deploy
  GH->>APR: Native backend auto deploy

  Dev->>TF: terraform plan for infra changes
  TF-->>Dev: Review planned resource changes
  Dev->>TF: terraform apply reviewed plan
  TF->>AWS: Create or update AWS infrastructure
```

## Responsibility Split

| Component | Responsibility |
|---|---|
| GitHub Actions CI | Validate code before merge |
| Terraform | Provision foundational AWS infrastructure through reviewed `plan/apply` |
| Amplify | Build and deploy Next.js frontend from GitHub |
| App Runner | Build and deploy FastAPI backend from GitHub/source |
| App Runner VPC connector | Private backend access to VPC resources |
| NAT Gateway | Public egress for backend calls when private VPC access is enabled |
| RDS PostgreSQL | Authoritative application data and pgvector-backed data |
| ElastiCache | Redis-compatible cache/session/rate-limit backend |
| S3 | Private storage for course/video assets |
| CloudFront | Public video streaming and asset delivery |
| Route 53 / ACM | DNS and HTTPS certificates |
| Secrets Manager | Secret containers and runtime secret values |
| CloudWatch / Budgets | Logs, alarms, and cost controls |

## Boundary Notes

- Terraform manages infrastructure, not large S3 objects or app releases.
- Course videos must stream `CloudFront -> Browser`, not through FastAPI.
- App Runner and Amplify use native AWS GitHub authorization for the first
  deployment. Import into Terraform later only if it improves drift control.
- Custom domains are attached only after temporary AWS domains pass smoke tests.
