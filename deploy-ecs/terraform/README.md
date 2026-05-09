# Terraform AWS Infrastructure — ECS

This directory manages AWS infrastructure for the ECS-first deployment.

## Stacks

- `bootstrap-state`: creates the S3 bucket for Terraform remote state
- `live/prod`: production infrastructure root module

## Local Commands

Bootstrap state once:

```bash
cd deploy-ecs/terraform/bootstrap-state
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

Initialize production:

```bash
cd deploy-ecs/terraform/live/prod
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive ../..
terraform validate
terraform plan -var-file=terraform.tfvars -out prod.tfplan
```

## Module Boundaries

- `network`: VPC, subnets, routes, NAT
- `security`: security groups and ingress/egress relationships
- `alb`: ALB, listeners, target groups
- `ecs_cluster`: shared ECS cluster primitives
- `ecs_service`: one service/task-definition unit
- `ecr`: image repositories
- `database`: RDS and subnet group
- `cache`: ElastiCache and subnet group
- `assets`: S3, OAC, CloudFront
- `observability`: budgets, alarms, log retention
- `iam_oidc`: GitHub Actions IAM roles

## Rules

- Do not commit `backend.hcl`, `*.tfvars`, `*.tfplan`, or state files
- Do not put real secret values in Terraform variables
- Terraform provisions infrastructure; GitHub Actions deploy app releases
- Run `terraform plan` before every `terraform apply`

## Current Status

This Terraform tree is a learning-oriented scaffold plus planning baseline.
Some modules are intentionally skeletal and document ownership boundaries rather
than a fully ready-to-apply production stack. Treat it as the source of truth
for decomposition and next implementation steps, not as a promise that every
module is production-complete today.
