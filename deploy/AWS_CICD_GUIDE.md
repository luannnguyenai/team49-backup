# AWS CI/CD Guide

Production CI/CD uses GitHub Actions with AWS OIDC. Do not use long-lived AWS access keys.

## Workflow model

```text
pull_request/main
  -> CI
     - backend lint/test
     - frontend lint/type-check/build/test

push main or workflow_dispatch
  -> deploy
     - reuse CI gate
     - assume AWS deploy role through OIDC
     - build backend image
     - push backend SHA tag to ECR
     - update backend App Runner service
     - smoke test backend
     - build frontend image
     - push frontend SHA tag to ECR
     - update frontend App Runner service
     - smoke test frontend

pull_request on deploy/terraform/** or workflow_dispatch
  -> terraform
     - assume AWS Terraform role through OIDC
     - write runtime-only backend.hcl
     - write runtime-only terraform.tfvars
     - terraform fmt/validate/plan
     - optional reviewed apply
```

## GitHub environment

Create a `production` GitHub Environment with:

- Required reviewer approval if production deploys should be manual-gated.
- Environment variables for non-secret identifiers.
- Secrets only for values that cannot be public.

## Required variables

| Name | Example |
|---|---|
| `AWS_REGION` | `ap-southeast-1` |
| `AWS_ACCOUNT_ID` | `123456789012` |
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-a20-prod-deploy` |
| `ECR_BACKEND_REPOSITORY` | `a20-backend` |
| `ECR_FRONTEND_REPOSITORY` | `a20-frontend` |
| `APP_RUNNER_BACKEND_SERVICE_ARN` | `arn:aws:apprunner:...:service/a20-backend/...` |
| `APP_RUNNER_FRONTEND_SERVICE_ARN` | `arn:aws:apprunner:...:service/a20-frontend/...` |
| `PRODUCTION_BACKEND_URL` | `https://api.<domain>` |
| `PRODUCTION_FRONTEND_URL` | `https://app.<domain>` |

## Required Terraform variables

| Name | Example |
|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-a20-prod-terraform` |
| `TF_BACKEND_HCL_PROD` | full `backend.hcl` file content |
| `TFVARS_PROD` | full `terraform.tfvars` file content |

## AWS IAM role

Trust policy must restrict access to this repository and the intended branch or GitHub environment.

The deploy role needs only:

- ECR auth and push/pull for backend/frontend repositories.
- App Runner read/update for backend/frontend services.
- CloudWatch read if deployment polling or log checks need it.

Terraform role needs only:

- S3 backend access to `a20-terraform-state-prod`.
- Create/read/update/delete permissions only for the Terraform-managed foundation resources.
- Route 53/ACM/CloudWatch/Budgets permissions only if those modules remain managed by Terraform.

Do not grant broad administrator access to the CI/CD role.

## Deployment tags

Use immutable tags:

```text
backend:<git-sha>
frontend:<git-sha>
```

Keep rollback simple by recording image digests in `GITHUB_STEP_SUMMARY`.

## Smoke tests

Backend:

```bash
curl --fail "$PRODUCTION_BACKEND_URL/health"
```

Frontend:

```bash
curl --fail "$PRODUCTION_FRONTEND_URL/api/health"
```

Add a catalog smoke test once stable production seed data exists.

## Rollback

Rollback by updating App Runner to a previous ECR image digest or SHA tag. Do not rebuild during rollback unless the old image was deleted.
