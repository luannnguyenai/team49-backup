# Terraform Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Terraform infrastructure-as-code for the AWS-first deployment so AWS infrastructure is reviewed with `terraform plan`, applied repeatably, and protected from console drift.

**Architecture:** Terraform manages infrastructure in `deploy/terraform/` using an S3 backend with native S3 state locking. Application deploys remain native Amplify/App Runner source auto deploy for v1. GitHub OAuth authorization, real secret values, object uploads, migrations, and bootstrap/import commands stay outside Terraform.

**Tech Stack:** Terraform CLI, HashiCorp AWS provider, AWS S3 backend with `use_lockfile`, AWS Amplify Hosting, AWS App Runner, RDS PostgreSQL, ElastiCache Redis OSS/Valkey, S3, CloudFront OAC, ACM, Route 53, CloudWatch, AWS Budgets, GitHub Actions OIDC for infrastructure automation.

---

## Design Rules

- `deploy/terraform/bootstrap-state` creates only the remote-state bucket.
- `deploy/terraform/live/prod` is the production root module.
- Bootstrap state and production state are separate.
- Real `backend.hcl`, `terraform.tfvars`, `*.tfplan`, and `*.tfstate` files are not committed.
- Terraform creates Secrets Manager containers, not real secret values.
- RDS master credentials use AWS-managed password when possible.
- Course/video assets are uploaded with AWS CLI after S3 exists; Terraform never tracks the 15 GB object set.
- `pgvector`, Alembic migrations, bootstrap/import, and S3-to-DB parity checks are explicit operator steps.
- App Runner and Amplify GitHub authorization is handled before Terraform creates/imports app resources.

## File Structure

```text
deploy/terraform/
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
      main.tf
      variables.tf
      outputs.tf
    assets/
      main.tf
      variables.tf
      outputs.tf
    database/
      main.tf
      variables.tf
      outputs.tf
    cache/
      main.tf
      variables.tf
      outputs.tf
    backend_apprunner/
      main.tf
      variables.tf
      outputs.tf
    frontend_amplify/
      main.tf
      variables.tf
      outputs.tf
    observability/
      main.tf
      variables.tf
      outputs.tf
```

## Task 1: Add Terraform Guardrails

**Files:**

- Modify: `.gitignore`
- Create: `deploy/terraform/README.md`

- [ ] **Step 1: Add ignore rules**

Append:

```gitignore
# Terraform
**/.terraform/
*.tfstate
*.tfstate.*
*.tfplan
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
*.tfvars
!*.tfvars.example
backend.hcl
!backend.hcl.example
```

- [ ] **Step 2: Create Terraform README**

Create `deploy/terraform/README.md`:

````markdown
# Terraform AWS Infrastructure

This directory manages AWS infrastructure for the AWS-first simple managed deployment.

## Stacks

- `bootstrap-state`: creates the S3 bucket for Terraform remote state.
- `live/prod`: production infrastructure root module.

## Local Commands

Bootstrap state once:

```bash
cd deploy/terraform/bootstrap-state
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

Initialize production:

```bash
cd deploy/terraform/live/prod
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive ../..
terraform validate
terraform plan -var-file=terraform.tfvars -out prod.tfplan
terraform apply prod.tfplan
```

## Rules

- Do not commit `backend.hcl`, `*.tfvars`, `*.tfplan`, or state files.
- Do not put real secret values in Terraform variables.
- Terraform provisions infrastructure; Amplify/App Runner deploy app code.
- Run `terraform plan` before every `terraform apply`.
````

- [ ] **Step 3: Verify**

Run:

```bash
git diff --check -- .gitignore deploy/terraform/README.md
```

Expected: no output.

## Task 2: Create Remote State Bootstrap Stack

**Files:**

- Create: `deploy/terraform/bootstrap-state/versions.tf`
- Create: `deploy/terraform/bootstrap-state/providers.tf`
- Create: `deploy/terraform/bootstrap-state/main.tf`
- Create: `deploy/terraform/bootstrap-state/outputs.tf`

- [ ] **Step 1: Define versions**

`versions.tf`:

```hcl
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

- [ ] **Step 2: Configure provider**

`providers.tf`:

```hcl
provider "aws" {
  region = "ap-southeast-1"

  default_tags {
    tags = {
      Project     = "a20"
      Environment = "prod"
      ManagedBy   = "terraform"
      Stack       = "terraform-state"
    }
  }
}
```

- [ ] **Step 3: Create state bucket**

`main.tf`:

```hcl
resource "aws_s3_bucket" "terraform_state" {
  bucket = "a20-terraform-state-prod"
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

- [ ] **Step 4: Add outputs**

`outputs.tf`:

```hcl
output "state_bucket_name" {
  value = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_region" {
  value = "ap-southeast-1"
}
```

- [ ] **Step 5: Validate**

Run:

```bash
cd deploy/terraform/bootstrap-state
terraform fmt -check
terraform init
terraform validate
terraform plan -out bootstrap.tfplan
```

Expected: plan creates the state bucket plus public access block, versioning, and encryption resources.

## Task 3: Create Production Root Module

**Files:**

- Create: `deploy/terraform/live/prod/backend.hcl.example`
- Create: `deploy/terraform/live/prod/terraform.tfvars.example`
- Create: `deploy/terraform/live/prod/versions.tf`
- Create: `deploy/terraform/live/prod/providers.tf`
- Create: `deploy/terraform/live/prod/locals.tf`
- Create: `deploy/terraform/live/prod/variables.tf`
- Create: `deploy/terraform/live/prod/main.tf`
- Create: `deploy/terraform/live/prod/outputs.tf`

- [ ] **Step 1: Add backend example**

`backend.hcl.example`:

```hcl
bucket       = "a20-terraform-state-prod"
key          = "a20/prod/terraform.tfstate"
region       = "ap-southeast-1"
use_lockfile = true
encrypt      = true
```

- [ ] **Step 2: Add variable example**

`terraform.tfvars.example`:

```hcl
project_name          = "a20"
environment           = "prod"
aws_region            = "ap-southeast-1"
domain_name           = "example.com"
enable_custom_domains = false
enable_nat_gateway    = true

github_repository_url = "https://github.com/<owner>/<repo>"
github_branch         = "main"

app_runner_connection_arn = ""
manage_amplify_in_terraform = false
amplify_app_id              = ""

backend_service_name = "a20-backend"
frontend_app_name    = "a20-frontend"
asset_bucket_name    = "a20-course-assets-prod"
asset_prefix         = "courses"
rds_identifier       = "a20-postgres-prod"
cache_identifier     = "a20-redis-prod"
budget_alert_email   = "ops@example.com"
```

- [ ] **Step 3: Add versions and providers**

`versions.tf`:

```hcl
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

`providers.tf`:

```hcl
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
```

- [ ] **Step 4: Add locals and variables**

`locals.tf`:

```hcl
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

`variables.tf`:

```hcl
variable "project_name" {
  type    = string
  default = "a20"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "aws_region" {
  type    = string
  default = "ap-southeast-1"
}

variable "domain_name" {
  type    = string
  default = "example.com"
}

variable "enable_custom_domains" {
  type    = bool
  default = false
}

variable "enable_nat_gateway" {
  type    = bool
  default = true
}

variable "github_repository_url" {
  type = string
}

variable "github_branch" {
  type    = string
  default = "main"
}

variable "app_runner_connection_arn" {
  type      = string
  default   = ""
  sensitive = true
}

variable "manage_amplify_in_terraform" {
  type    = bool
  default = false
}

variable "amplify_app_id" {
  type    = string
  default = ""
}

variable "backend_service_name" {
  type    = string
  default = "a20-backend"
}

variable "frontend_app_name" {
  type    = string
  default = "a20-frontend"
}

variable "asset_bucket_name" {
  type    = string
  default = "a20-course-assets-prod"
}

variable "asset_prefix" {
  type    = string
  default = "courses"
}

variable "rds_identifier" {
  type    = string
  default = "a20-postgres-prod"
}

variable "cache_identifier" {
  type    = string
  default = "a20-redis-prod"
}

variable "budget_alert_email" {
  type = string
}
```

- [ ] **Step 5: Add empty root**

`main.tf`:

```hcl
# Modules are wired in later tasks.
```

`outputs.tf`:

```hcl
output "project_name" {
  value = var.project_name
}

output "environment" {
  value = var.environment
}
```

- [ ] **Step 6: Validate empty root**

Run:

```bash
cd deploy/terraform/live/prod
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars -out prod-empty.tfplan
```

Expected: plan succeeds with no infrastructure changes.

## Task 4: Add Network Module

**Files:**

- Create: `deploy/terraform/modules/network/main.tf`
- Create: `deploy/terraform/modules/network/variables.tf`
- Create: `deploy/terraform/modules/network/outputs.tf`
- Modify: `deploy/terraform/live/prod/main.tf`
- Modify: `deploy/terraform/live/prod/outputs.tf`

- [ ] **Step 1: Add variables**

`variables.tf`:

```hcl
variable "name_prefix" {
  type = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "availability_zone_count" {
  type    = number
  default = 2
}

variable "enable_nat_gateway" {
  type = bool
}
```

- [ ] **Step 2: Add VPC, subnets, routes, and security groups**

`main.tf`:

```hcl
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "public" {
  count                   = var.availability_zone_count
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count             = var.availability_zone_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  count          = var.availability_zone_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"
}

resource "aws_nat_gateway" "this" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
}

resource "aws_route" "private_nat_egress" {
  count                  = var.enable_nat_gateway ? 1 : 0
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[0].id
}

resource "aws_route_table_association" "private" {
  count          = var.availability_zone_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "app_runner" {
  name        = "${var.name_prefix}-apprunner"
  description = "App Runner VPC connector egress"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group_rule" "app_runner_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app_runner.id
}

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds"
  description = "RDS PostgreSQL from App Runner"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group_rule" "rds_from_app_runner" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.app_runner.id
}

resource "aws_security_group" "cache" {
  name        = "${var.name_prefix}-cache"
  description = "Redis from App Runner"
  vpc_id      = aws_vpc.this.id
}

resource "aws_security_group_rule" "cache_from_app_runner" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.cache.id
  source_security_group_id = aws_security_group.app_runner.id
}
```

- [ ] **Step 3: Add outputs**

`outputs.tf`:

```hcl
output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "app_runner_security_group_id" {
  value = aws_security_group.app_runner.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "cache_security_group_id" {
  value = aws_security_group.cache.id
}
```

- [ ] **Step 4: Wire root**

Add to `live/prod/main.tf`:

```hcl
module "network" {
  source = "../../modules/network"

  name_prefix        = local.name_prefix
  enable_nat_gateway = var.enable_nat_gateway
}
```

Add to `live/prod/outputs.tf`:

```hcl
output "vpc_id" {
  value = module.network.vpc_id
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}
```

- [ ] **Step 5: Plan**

Run:

```bash
cd deploy/terraform/live/prod
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out prod-network.tfplan
```

Expected: plan includes VPC, public/private subnets, public/private route tables, route associations, security groups, and NAT only when enabled.

## Task 5: Add Assets Module

**Files:**

- Create: `deploy/terraform/modules/assets/main.tf`
- Create: `deploy/terraform/modules/assets/variables.tf`
- Create: `deploy/terraform/modules/assets/outputs.tf`
- Modify: `deploy/terraform/live/prod/main.tf`
- Modify: `deploy/terraform/live/prod/outputs.tf`

**Module responsibilities:**

- S3 bucket.
- Public access block.
- Versioning.
- Default encryption.
- CloudFront OAC.
- CloudFront distribution using the S3 regional domain.
- Bucket policy granting CloudFront access only through the distribution.

**Important:** Do not manage `aws_s3_object` for course assets.

- [ ] **Step 1: Implement module**

Include these resource types in `main.tf`:

```hcl
aws_s3_bucket
aws_s3_bucket_public_access_block
aws_s3_bucket_versioning
aws_s3_bucket_server_side_encryption_configuration
aws_cloudfront_origin_access_control
aws_cloudfront_distribution
aws_s3_bucket_policy
```

- [ ] **Step 2: Wire root**

```hcl
module "assets" {
  source = "../../modules/assets"

  name_prefix  = local.name_prefix
  bucket_name  = var.asset_bucket_name
  asset_prefix = var.asset_prefix
}
```

- [ ] **Step 3: Plan**

Run:

```bash
cd deploy/terraform/live/prod
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out prod-assets.tfplan
```

Expected: plan creates private S3/CDN resources and no S3 objects.

## Task 6: Add Database And Cache Modules

**Files:**

- Create: `deploy/terraform/modules/database/main.tf`
- Create: `deploy/terraform/modules/database/variables.tf`
- Create: `deploy/terraform/modules/database/outputs.tf`
- Create: `deploy/terraform/modules/cache/main.tf`
- Create: `deploy/terraform/modules/cache/variables.tf`
- Create: `deploy/terraform/modules/cache/outputs.tf`
- Modify: `deploy/terraform/live/prod/main.tf`
- Modify: `deploy/terraform/live/prod/outputs.tf`

**Database requirements:**

- RDS PostgreSQL.
- Private DB subnet group.
- `publicly_accessible = false`.
- Automated backups.
- Deletion protection.
- Storage autoscaling cap.
- `manage_master_user_password = true`.

**Cache requirements:**

- ElastiCache Redis OSS or Valkey.
- Private subnet group.
- Security group from network module.
- Single small node for v1 unless requirements change.
- Endpoint and port outputs only.

- [ ] **Step 1: Wire root**

```hcl
module "database" {
  source = "../../modules/database"

  identifier         = var.rds_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.rds_security_group_id
  instance_class     = "db.t4g.micro"
}

module "cache" {
  source = "../../modules/cache"

  identifier         = var.cache_identifier
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.cache_security_group_id
  node_type          = "cache.t4g.micro"
}
```

- [ ] **Step 2: Plan**

Run:

```bash
cd deploy/terraform/live/prod
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out prod-data.tfplan
```

Expected: plan creates private RDS and cache resources without DB passwords in `.tfvars`.

- [ ] **Step 3: Record post-apply SQL**

After RDS apply, run from a trusted environment that can reach RDS:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

Expected: query returns `vector`.

## Task 7: Add App Runner And Amplify Modules

**Files:**

- Create: `deploy/terraform/modules/backend_apprunner/main.tf`
- Create: `deploy/terraform/modules/backend_apprunner/variables.tf`
- Create: `deploy/terraform/modules/backend_apprunner/outputs.tf`
- Create: `deploy/terraform/modules/frontend_amplify/main.tf`
- Create: `deploy/terraform/modules/frontend_amplify/variables.tf`
- Create: `deploy/terraform/modules/frontend_amplify/outputs.tf`
- Modify: `deploy/terraform/live/prod/main.tf`
- Modify: `deploy/terraform/live/prod/outputs.tf`

**App Runner rule:**

- `app_runner_connection_arn` must be supplied after GitHub authorization.
- If the connection ARN is empty, the module must create zero App Runner service
  resources and output an empty service URL.

**Amplify rule:**

- Preferred v1 path is manual authorization/import to avoid access tokens in
  Terraform state.
- If `manage_amplify_in_terraform = false`, module creates no resources and the
  operator records the manual Amplify app ID.
- If Terraform manages Amplify, the team must explicitly accept token/state
  tradeoffs before adding token variables.

- [ ] **Step 1: Wire root**

```hcl
module "backend_apprunner" {
  source = "../../modules/backend_apprunner"

  service_name       = var.backend_service_name
  repository_url     = var.github_repository_url
  branch_name        = var.github_branch
  connection_arn     = var.app_runner_connection_arn
  private_subnet_ids = module.network.private_subnet_ids
  security_group_id  = module.network.app_runner_security_group_id
}

module "frontend_amplify" {
  source = "../../modules/frontend_amplify"

  count               = var.manage_amplify_in_terraform ? 1 : 0
  app_name            = var.frontend_app_name
  repository_url      = var.github_repository_url
  branch_name         = var.github_branch
  backend_url         = module.backend_apprunner.service_url
}
```

- [ ] **Step 2: Plan**

Run:

```bash
cd deploy/terraform/live/prod
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out prod-apps.tfplan
```

Expected: App Runner resources appear only when the connection ARN is present. Amplify resources appear only when `manage_amplify_in_terraform = true`.

## Task 8: Add Domains And Observability

**Files:**

- Create: `deploy/terraform/modules/observability/main.tf`
- Create: `deploy/terraform/modules/observability/variables.tf`
- Create: `deploy/terraform/modules/observability/outputs.tf`
- Modify: `deploy/terraform/modules/assets/**`
- Modify: `deploy/terraform/modules/backend_apprunner/**`
- Modify: `deploy/terraform/modules/frontend_amplify/**`
- Modify: `deploy/terraform/live/prod/**`

**Observability resources:**

- AWS Budget monthly cost alert.
- CloudFront bytes downloaded alarm.
- App Runner 5xx/service health alarm.
- RDS CPU/free storage alarms.
- CloudWatch log retention when log group names are known.
- NAT spend review alarm or budget note when NAT is enabled.

**Domain resources:**

- Route 53 records when `enable_custom_domains = true`.
- ACM certificates in primary region for App Runner/Amplify where applicable.
- ACM certificate in `us-east-1` for CloudFront alternate domain.

- [ ] **Step 1: Plan without custom domains**

Run with `enable_custom_domains = false`:

```bash
terraform plan -var-file=terraform.tfvars -out prod-ops.tfplan
```

Expected: observability resources only.

- [ ] **Step 2: Plan with custom domains**

Run after setting `enable_custom_domains = true` and a real `domain_name`:

```bash
terraform plan -var-file=terraform.tfvars -out prod-domains.tfplan
```

Expected: Route 53, ACM, and service domain resources are included.

## Task 9: Add Terraform Infrastructure CI

**Files:**

- Create: `.github/workflows/terraform.yml`
- Modify: `deploy/AWS_CICD_GUIDE.md`
- Modify: `deploy/ENVIRONMENT_MATRIX.md`

**CI design:**

- Terraform CI is separate from app CI/CD.
- Pull requests run `fmt`, `validate`, and `plan`.
- Manual `workflow_dispatch` can apply only after review.
- GitHub Actions must create `backend.hcl` and `terraform.tfvars` at runtime
  from protected GitHub Environment secrets or variables because those files are
  not committed.

**Required GitHub Environment values:**

| Name | Type | Purpose |
|---|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | secret | OIDC role for Terraform |
| `TF_BACKEND_HCL_PROD` | secret or protected variable | Full `backend.hcl` content |
| `TFVARS_PROD` | secret or protected variable | Full non-committed `terraform.tfvars` content |

- [ ] **Step 1: Create workflow**

The workflow must include runtime file creation before `terraform init`:

```yaml
name: Terraform

on:
  pull_request:
    paths:
      - "deploy/terraform/**"
      - ".github/workflows/terraform.yml"
  workflow_dispatch:
    inputs:
      apply:
        description: "Apply reviewed production Terraform plan"
        required: true
        default: "false"
        type: choice
        options:
          - "false"
          - "true"

permissions:
  contents: read
  id-token: write
  pull-requests: read

concurrency:
  group: terraform-prod
  cancel-in-progress: false

jobs:
  plan:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_TERRAFORM_ROLE_ARN }}
          aws-region: ap-southeast-1
      - name: Write backend config
        working-directory: deploy/terraform/live/prod
        run: printf '%s' "${{ secrets.TF_BACKEND_HCL_PROD }}" > backend.hcl
      - name: Write production variables
        working-directory: deploy/terraform/live/prod
        run: printf '%s' "${{ secrets.TFVARS_PROD }}" > terraform.tfvars
      - name: Terraform init
        working-directory: deploy/terraform/live/prod
        run: terraform init -backend-config=backend.hcl
      - name: Terraform fmt
        working-directory: deploy/terraform
        run: terraform fmt -check -recursive
      - name: Terraform validate
        working-directory: deploy/terraform/live/prod
        run: terraform validate
      - name: Terraform plan
        working-directory: deploy/terraform/live/prod
        run: terraform plan -var-file=terraform.tfvars -out prod.tfplan
      - name: Terraform apply
        if: ${{ github.event_name == 'workflow_dispatch' && inputs.apply == 'true' }}
        working-directory: deploy/terraform/live/prod
        run: terraform apply -auto-approve prod.tfplan
```

- [ ] **Step 2: Validate docs/workflow**

Run:

```bash
git diff --check -- .github/workflows/terraform.yml deploy/AWS_CICD_GUIDE.md deploy/ENVIRONMENT_MATRIX.md
```

Expected: no whitespace errors.

## Task 10: Final Documentation Alignment

**Files:**

- Modify: `deploy/README.md`
- Modify: `deploy/DEPLOYMENT_PLAN.md`
- Modify: `deploy/AWS_CONFIG_GUIDE.md`
- Modify: `deploy/MANUAL_DEPLOY_STEPS.md`
- Modify: `deploy/PRODUCTION_CHECKLIST.md`
- Modify: `deploy/ENVIRONMENT_MATRIX.md`
- Modify: `deploy/AWS_CICD_GUIDE.md`
- Modify: `deploy/AWS_ARCHITECTURE.md`
- Modify: `deploy/PLATFORM_ANALYSIS.md`

- [ ] **Step 1: Confirm Terraform-first wording**

Scan:

```bash
rg -n "create-bucket|console|manual" deploy -g "*.md"
```

Expected: manual infra creation is described only as a fallback or an OAuth/secret/upload/migration/bootstrap operation.

- [ ] **Step 2: Confirm no legacy app deploy recommendation remains**

Run:

```bash
rg -n "Vercel|Railway|Supabase|ECR|OIDC" deploy -g "*.md"
```

Expected: Vercel/Railway/Supabase appear only as legacy workflow warnings. ECR/OIDC appears only as optional later hardening or Terraform infra OIDC.

- [ ] **Step 3: Confirm route-table coverage**

Run:

```bash
rg -n "route table|aws_route_table|aws_route_table_association|private_nat_egress" deploy/TERRAFORM_PLAN.md
```

Expected: route table resources are present in the network task.
