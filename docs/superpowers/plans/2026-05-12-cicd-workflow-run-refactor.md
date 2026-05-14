# CI/CD Workflow Run Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor GitHub Actions release orchestration from reusable CI-in-deploy to a `CI -> Build & Push -> Deploy` `workflow_run` chain while preserving existing ECS deployment behavior.

**Architecture:** Keep `ci.yml` as the standalone validation workflow. Add a dedicated image build workflow that listens for successful CI runs on `main`, then refactor deploy to listen for successful build runs and deploy images tagged with the upstream commit SHA.

**Tech Stack:** GitHub Actions, AWS OIDC, Amazon ECR, Amazon ECS, Bash, Docker.

---

### Task 1: Add Build Workflow

**Files:**
- Create: `.github/workflows/build-push.yml`

- [ ] Define a `workflow_run` build workflow for `CI` plus manual dispatch.
- [ ] Run on `[self-hosted]` and use production-scoped AWS vars/secrets.
- [ ] Check out `workflow_run.head_sha` when triggered automatically.
- [ ] Build and push backend/frontend images tagged by commit SHA.

### Task 2: Refactor Deploy Trigger

**Files:**
- Modify: `.github/workflows/deploy-ecs-prod.yml`

- [ ] Replace `push` trigger and reusable `ci` job with `workflow_run` from `Build & Push to ECR`.
- [ ] Change runner to `[self-hosted]`.
- [ ] Update image tag resolution to use `workflow_run.head_sha` for automatic deploys.
- [ ] Remove image build/push steps from deploy while preserving deploy, migration, bootstrap, and smoke logic.

### Task 3: Verify Workflow Integrity

**Files:**
- Modify: `.github/workflows/build-push.yml`
- Modify: `.github/workflows/deploy-ecs-prod.yml`

- [ ] Parse workflow YAML locally.
- [ ] Inspect the resulting trigger chain and key runner/credential settings.
- [ ] Summarize any remaining operational assumptions for GitHub environment config.
