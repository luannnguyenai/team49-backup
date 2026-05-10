# CI/CD Review Package

This folder contains the ECS CI/CD plan and review artifacts for the current
`deploy-ecs/` production path.

It is intentionally separate from `.github/workflows/` so Claude or another
reviewer can inspect the plan before any production workflow is activated.

## Contents

- `ECS_CICD_PLAN.md`: implementation plan for ECS production CI/CD.
- `REVIEW_CHECKLIST.md`: review gates and failure modes to block.
- `workflows/`: draft GitHub Actions workflows, not active until copied into
  `.github/workflows/`.
- `taskdefs/`: reusable ECS task definition templates without account-specific
  ARNs or image tags.
- `scripts/`: shell helpers used by the workflow drafts.

## Current Decision

Use `deploy-ecs/` as the production target:

- Terraform owns stable infrastructure in `deploy-ecs/terraform`.
- GitHub Actions owns app releases after ECS services exist.
- Releases use immutable ECR SHA tags, ECS task definition revisions, ECS
  service updates, and ALB smoke checks.
- Database migrations run as one-off ECS tasks, never in long-running service
  startup commands.

## Promotion Rule

Do not copy anything from `cicd/workflows/` into `.github/workflows/` until the
review checklist passes and the required GitHub production variables/secrets
exist.
