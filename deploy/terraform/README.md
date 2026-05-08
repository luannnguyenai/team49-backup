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

## App Runner And Amplify Ownership

For the first production deploy, create App Runner and Amplify through AWS native
GitHub authorization. Terraform manages foundational infrastructure first. After
the backend and frontend default AWS domains are healthy, app-service resources
may be imported into Terraform if doing so reduces drift without storing GitHub
tokens or real secret values in state.
