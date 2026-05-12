# ECS Initialization Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-safe ECS initialization workflow that reproduces the important data-init behavior of local `start.sh` without coupling it to service startup.

**Architecture:** Keep deploy and data initialization separate. Add a manual GitHub Actions workflow that runs one-off ECS tasks using the backend image, add dedicated task definitions and log groups, and harden the ECS run-task helper so failures surface logs clearly.

**Tech Stack:** GitHub Actions, Amazon ECS Fargate, AWS CloudWatch Logs, Terraform, Bash, Python.

---

### Task 1: Add ECS Init Workflow

**Files:**
- Create: `.github/workflows/init-ecs-prod.yml`
- Modify: `.github/workflows/deploy-ecs-prod.yml`

- [ ] Add a manual `Initialize ECS Production` workflow with image-tag resolution and per-phase flags.
- [ ] Keep deploy focused on backend/frontend rollout and migrations only.
- [ ] Remove broad bootstrap behavior from the deploy workflow.

### Task 2: Add One-Off Task Definitions

**Files:**
- Create: `cicd/taskdefs/backend-seed-core.json.tpl`
- Create: `cicd/taskdefs/backend-sync-schema-v2.json.tpl`
- Create: `cicd/taskdefs/backend-seed-accounts.json.tpl`

- [ ] Create one taskdef per init responsibility.
- [ ] Keep commands small and intention-revealing.
- [ ] Reuse the deployed backend image and current ECS network/security model.

### Task 3: Harden Task Execution And Logging

**Files:**
- Modify: `cicd/scripts/run-ecs-task.sh`
- Modify: `deploy-ecs/terraform/modules/iam_oidc/main.tf`

- [ ] Add timeout-driven polling for one-off ECS tasks.
- [ ] Fetch recent CloudWatch logs when a task exits non-zero.
- [ ] Grant the GitHub deploy role minimal CloudWatch Logs read permissions needed for failure diagnostics.

### Task 4: Add Observability Support

**Files:**
- Modify: `deploy-ecs/terraform/modules/observability/main.tf`
- Modify: `deploy-ecs/terraform/modules/observability/outputs.tf`

- [ ] Add dedicated log groups for new init task families.
- [ ] Expose outputs for consistency with existing backend/frontend/migrate log groups.

### Task 5: Verify Workflow And Template Integrity

**Files:**
- Modify: `.github/workflows/init-ecs-prod.yml`
- Modify: `.github/workflows/deploy-ecs-prod.yml`
- Modify: `cicd/taskdefs/backend-seed-core.json.tpl`
- Modify: `cicd/taskdefs/backend-sync-schema-v2.json.tpl`
- Modify: `cicd/taskdefs/backend-seed-accounts.json.tpl`
- Modify: `cicd/scripts/run-ecs-task.sh`

- [ ] Parse all workflow YAML files locally.
- [ ] Render task definitions locally with stub env vars to confirm placeholders resolve.
- [ ] Run a targeted Terraform apply for IAM and log groups if needed to unblock production use.
