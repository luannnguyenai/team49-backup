# ECS Initialization Workflow Design

## Goal

Make production ECS initialization equivalent to the important post-start behavior of local `start.sh` without turning the long-running ECS services into bootstrap scripts. Keep deploy and data-init separate so releases stay stable while initialization remains rerunnable and observable.

## Problem

Local `start.sh` does more than start services: it runs migrations, imports canonical/product-shell data, seeds lectures, syncs Schema v2, validates parity, and creates admin/demo accounts. ECS deploy currently performs only service rollout plus migrations, so production can diverge from localhost even when the same image is deployed.

## Chosen Approach

Add a dedicated manual workflow, `Initialize ECS Production`, that runs one-off ECS Fargate tasks using the deployed backend image. Keep `Deploy ECS Production` focused on backend/frontend rollout and database migration only.

This preserves production-safe behavior:

- service startup stays thin and restart-safe
- initialization tasks can be rerun independently
- failures are isolated by phase
- logs are attributable to specific one-off tasks

## Alternatives Considered

### 1. Put all bootstrap logic into backend startup

Rejected. That would rerun initialization on every restart or scale-out event and couples production readiness to data bootstrap timing.

### 2. Keep one giant bootstrap ECS task

Rejected. The existing `backend-bootstrap.json.tpl` bundles too many independent concerns, making failures hard to isolate and reruns too coarse.

### 3. Split initialization into a dedicated workflow with small task groups

Accepted. This is the best balance between operational safety and fidelity to local startup.

## Target Workflow Shape

### Release Workflow

`Deploy ECS Production` remains responsible for:

- deploy backend service
- run one-off Alembic migration task
- deploy frontend service
- run service and HTTP smoke checks

It no longer owns broad bootstrap behavior.

### Initialization Workflow

New workflow: `.github/workflows/init-ecs-prod.yml`

Trigger:

- `workflow_dispatch` only

Inputs:

- `run_seed_core`
- `run_sync_schema_v2`
- `run_seed_accounts`
- `smoke_after_init`
- `image_tag`

## Task Groups

### 1. Seed Core

Runs the backend image as a one-off ECS task with:

`uv run python scripts/seed.py`

Purpose:

- import canonical content
- import product shell
- seed lectures
- run parity report included in `seed.py`

### 2. Sync Schema V2

Runs:

`uv run python -m src.scripts.schema_v2.sync_schema_v2`

Purpose:

- rerun safe schema migration
- backfill Schema v2
- validate Schema v2
- run parity check

### 3. Seed Accounts

Runs:

`uv run python -m src.scripts.create_seed_accounts`

Purpose:

- ensure admin/demo accounts exist via upsert logic

## Infrastructure Changes

Create dedicated CloudWatch log groups for each init task family:

- `/ecs/<backend>-seed-core`
- `/ecs/<backend>-sync-schema-v2`
- `/ecs/<backend>-seed-accounts`

Enhance the GitHub deploy role so it can fetch CloudWatch log streams when one-off tasks fail.

## Script Hardening

Enhance `cicd/scripts/run-ecs-task.sh` to:

- poll task status with a timeout instead of waiting blindly
- report non-zero container exit codes
- print recent CloudWatch log events from the configured log group on failure

## Operational Model

Recommended operator sequence:

1. Run `Deploy ECS Production`
2. Run `Initialize ECS Production`
3. Verify `/api/course-sections`
4. Verify admin/demo login if relevant

Initialization stays manual by default so production data mutations remain intentional.
