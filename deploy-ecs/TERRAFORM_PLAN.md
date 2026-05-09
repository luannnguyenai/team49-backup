# ECS Terraform Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Terraform infrastructure-as-code for the ECS-first deployment so AWS infrastructure is reviewed with `terraform plan`, applied repeatably, and protected from console drift.

**Architecture:** Terraform manages foundational infrastructure in `deploy-ecs/terraform/` using an S3 backend with native S3 locking. Application deploys remain GitHub Actions driven: build images, push ECR, register task definition revisions, and update ECS services. Terraform owns the stable infrastructure graph: network, ALB, ECS cluster/service primitives, ECR, database, cache, assets, IAM, and observability.

**Tech Stack:** Terraform CLI, HashiCorp AWS provider, AWS S3 backend, Amazon ECS on Fargate, ALB, ECR, RDS PostgreSQL, ElastiCache Redis OSS/Valkey, S3, CloudFront OAC, ACM, Route 53, CloudWatch, AWS Budgets, GitHub Actions OIDC.

---

## Design Rules

- `deploy-ecs/terraform/bootstrap-state` creates only the remote-state bucket.
- `deploy-ecs/terraform/live/prod` is the production root module.
- Real `backend.hcl`, `terraform.tfvars`, `*.tfstate`, and `*.tfplan` files are not committed.
- Terraform creates infrastructure and IAM roles, not real secret values.
- Terraform does not upload 15 GB of course assets.
- Terraform does not run `pgvector`, migrations, or bootstrap/import commands.
- Frontend and backend ECS services stay separate, even when sharing one cluster.

## File Structure

```text
deploy-ecs/terraform/
  README.md
  bootstrap-state/
    versions.tf
    providers.tf
    main.tf
    outputs.tf
  live/
    prod/
      backend.hcl.example
      terraform.tfvars.example
      versions.tf
      providers.tf
      locals.tf
      variables.tf
      main.tf
      outputs.tf
  modules/
    network/
    security/
    alb/
    ecs_cluster/
    ecs_service/
    ecr/
    database/
    cache/
    assets/
    observability/
    iam_oidc/
```

## Definition Of Done

- Root Terraform scaffold exists and validates structurally
- Module boundaries are documented and reflected in file layout
- Terraform examples are safe to copy locally without embedding secrets
- The plan explains how to wire ECS, ALB, ECR, RDS, Redis, S3, CloudFront, and IAM OIDC

## Task Sequence

### Task 1: Add Terraform guardrails

**Files:**

- Create: `deploy-ecs/terraform/README.md`

- [ ] Document local `terraform init`, `plan`, and `apply` commands
- [ ] Document non-committed files and secret boundaries
- [ ] Record module responsibilities

### Task 2: Create remote state bootstrap stack

**Files:**

- Create: `deploy-ecs/terraform/bootstrap-state/versions.tf`
- Create: `deploy-ecs/terraform/bootstrap-state/providers.tf`
- Create: `deploy-ecs/terraform/bootstrap-state/main.tf`
- Create: `deploy-ecs/terraform/bootstrap-state/outputs.tf`

- [ ] Define AWS provider and Terraform version constraints
- [ ] Create the S3 state bucket with encryption and versioning
- [ ] Output state bucket details

### Task 3: Create production root module

**Files:**

- Create: `deploy-ecs/terraform/live/prod/backend.hcl.example`
- Create: `deploy-ecs/terraform/live/prod/terraform.tfvars.example`
- Create: `deploy-ecs/terraform/live/prod/versions.tf`
- Create: `deploy-ecs/terraform/live/prod/providers.tf`
- Create: `deploy-ecs/terraform/live/prod/locals.tf`
- Create: `deploy-ecs/terraform/live/prod/variables.tf`
- Create: `deploy-ecs/terraform/live/prod/main.tf`
- Create: `deploy-ecs/terraform/live/prod/outputs.tf`

- [ ] Define safe examples for backend and tfvars
- [ ] Define shared locals and tags
- [ ] Wire module boundaries in root `main.tf`

### Task 4: Add core infrastructure modules

**Files:**

- Create module skeletons under `deploy-ecs/terraform/modules/*`

- [ ] `network`: VPC, subnets, routes
- [ ] `security`: SG relationships
- [ ] `alb`: ALB, listeners, target groups
- [ ] `ecs_cluster`: cluster, capacity providers baseline, logging primitives
- [ ] `ecs_service`: task definition, service, autoscaling hooks
- [ ] `ecr`: repositories and lifecycle
- [ ] `database`: RDS subnet group and instance
- [ ] `cache`: ElastiCache subnet group and cluster
- [ ] `assets`: S3, OAC, CloudFront
- [ ] `observability`: alarms, budgets, retention
- [ ] `iam_oidc`: GitHub OIDC roles

### Task 5: Wire CI/CD and runtime docs

**Files:**

- `deploy-ecs/AWS_CICD_GUIDE.md`
- `deploy-ecs/ENVIRONMENT_MATRIX.md`
- `deploy-ecs/MANUAL_DEPLOY_STEPS.md`

- [ ] Document ECS image rollout flow
- [ ] Document task definition revision strategy
- [ ] Document rollback using previous task definitions

### Task 6: Final self-review

- [ ] Placeholder scan
- [ ] Cross-doc consistency check
- [ ] Confirm App Runner wording does not remain in ECS docs except as comparison
