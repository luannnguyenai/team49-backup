# Main to Hybrid Port Tasks

## Purpose

This task list defines how to selectively port infrastructure and persistence improvements from `main` into `hybrid/integrate-db-review` without regressing the current course-first product direction.

Rules:

- `hybrid/integrate-db-review` stays the product baseline
- only infra/runtime/persistence improvements from `main` are candidates
- no task in this file should restore auth-first root flow or tutor-first product behavior

## Phase 1: Audit and Snapshot

- [x] T001 Create a focused diff snapshot for `main` vs `hybrid` in `docs/MAIN_VS_HYBRID_REVIEW.md` and `docs/MAIN_TO_HYBRID_PORT_TASKS.md`
- [x] T002 Inspect `main` commit `cc14d53` and record touched runtime/database files in `docs/MAIN_TO_HYBRID_PORT_TASKS.md`
- [x] T003 Capture current hybrid baseline verification commands and outputs in `docs/hybrid-integration-review.md`
- [x] T004 [P] Export `main` versions of `docker-compose.yml`, `start.sh`, `pyproject.toml`, `uv.lock`, and Alembic files into a temporary comparison note in `docs/MAIN_TO_HYBRID_PORT_TASKS.md`

## Phase 2: Decide What Is Safe to Port

- [x] T005 Review `main:docker-compose.yml` against `hybrid:docker-compose.yml` and document `keep / port / avoid` decisions in `docs/MAIN_VS_HYBRID_REVIEW.md`
- [x] T006 Review `main:start.sh` against `hybrid:start.sh` and document `keep / port / avoid` decisions in `docs/MAIN_VS_HYBRID_REVIEW.md`
- [x] T007 Review `main` Alembic revisions and `schema v1` changes against `hybrid/alembic/versions/*` and record compatibility notes in `docs/hybrid-merge-conflicts.md`
- [x] T008 Review `main` dependency/runtime changes in `pyproject.toml`, `requirements.txt`, and `uv.lock` and classify them in `docs/MAIN_VS_HYBRID_REVIEW.md`
- [x] T009 [P] Review `main` database features related to `pgvector` in `src/database.py`, migrations, and compose/runtime files, then record adoption criteria in `docs/MAIN_TO_HYBRID_PORT_TASKS.md`

## Phase 3: Port Runtime and Ops Improvements

- [x] T010 Port safe startup/runtime changes from `main:start.sh` into `hybrid/start.sh`
- [x] T011 Port safe compose/runtime changes from `main:docker-compose.yml` into `hybrid/docker-compose.yml`
- [x] T012 Port safe dependency/runtime changes from `main:pyproject.toml` and `main:uv.lock` into `hybrid/pyproject.toml` and `hybrid/uv.lock`
- [x] T013 [P] Update `hybrid/requirements.txt` if `main` introduced runtime-critical package alignment in `requirements.txt`
- [x] T014 Add or update runtime verification coverage for startup and compose behavior in `tests/test_docker_compose_healthcheck.py` and `tests/test_app_lifespan.py`

## Phase 4: Port Database and Migration Improvements

- [ ] T015 Review `main` Alembic head topology and reconcile it with `hybrid/alembic/versions/*` before copying any revision files
- [ ] T016 Port only non-conflicting migration improvements from `main/alembic/versions/*` into `hybrid/alembic/versions/*`
- [ ] T017 Update `hybrid/alembic.ini` if `main` contains safer or more consistent migration/runtime settings
- [x] T018 Integrate approved `pgvector` setup changes from `main` into `hybrid/docker-compose.yml`, `hybrid/pyproject.toml`, and any related migration files
- [ ] T019 Add regression coverage for migration topology and extension setup in `tests/test_alembic_heads.py` and a new migration/runtime test file under `tests/`

## Phase 5: Strengthen Hybrid Persistence Without Regressing Product Flow

- [ ] T020 Audit whether any `main` schema changes should be reflected in `hybrid/src/models/learning.py` without altering `hybrid/src/models/course.py`
- [ ] T021 Port safe persistence refinements from `main/src/models/learning.py` into `hybrid/src/models/learning.py`
- [ ] T022 Review whether `main` startup/schema changes require updates to `hybrid/src/database.py` and `hybrid/src/config.py`
- [ ] T023 Apply only DB-authoritative improvements that help replace bootstrap reliance in `hybrid/src/services/course_bootstrap_service.py` and `hybrid/src/services/course_catalog_service.py`
- [ ] T024 [P] Extend repository or service tests affected by schema/runtime changes in `tests/repositories/*.py` and `tests/contract/*.py`

## Phase 6: Verification and Guardrails

- [ ] T025 Run backend regression suite covering config, startup, auth, and course APIs with `tests/test_config.py`, `tests/test_app_lifespan.py`, `tests/test_health.py`, and `tests/contract/*.py`
- [ ] T026 Run repository and persistence regression suite under `tests/repositories/*.py`
- [ ] T027 Run frontend regression suite for course-first flows in `frontend/tests/routes/*.tsx` and `frontend/tests/unit/*.ts*`
- [ ] T028 Run Playwright smoke coverage in `frontend/tests/e2e/course-discovery.spec.ts`, `frontend/tests/e2e/course-gating.spec.ts`, and `frontend/tests/e2e/lecture-tutor.spec.ts`
- [ ] T029 Record final verification evidence and any residual risks in `docs/hybrid-integration-review.md`

## Phase 7: Final Decision and Merge Prep

- [ ] T030 Update `docs/MAIN_VS_HYBRID_REVIEW.md` with what was actually ported from `main`
- [ ] T031 Update `docs/course-first-refactor-architecture.md` and `docs/hybrid-system-design.md` if runtime or persistence assumptions changed
- [ ] T032 Prepare a concise merge summary listing all `main`-derived changes and impacted files in a new section inside `docs/hybrid-integration-review.md`
- [ ] T033 Create a final checkpoint commit on `hybrid/integrate-db-review` after all verification passes

## Dependencies

- Phase 1 must complete before Phase 2.
- Phase 2 must complete before any code port in Phase 3 or Phase 4.
- Phase 3 and Phase 4 may overlap only after explicit safe-port decisions are recorded.
- Phase 5 depends on the finalized schema/runtime direction from Phase 4.
- Phase 6 depends on all implementation phases.
- Phase 7 depends on successful verification in Phase 6.

## Parallel Opportunities

- T004 and T009 can run in parallel during the audit.
- T013 and T014 can run in parallel once runtime choices are finalized.
- T024 can be split by repository/service area after schema decisions settle.

## Suggested Execution Order

1. Finish the audit and safe-port decisions first.
2. Port runtime/ops changes from `main`.
3. Port only the database/migration improvements that fit hybrid’s canonical course-first model.
4. Re-run the full hybrid verification baseline.
5. Only then prepare the branch for merge discussion.

## Current Notes

- `pgvector` was selected as a safe compose/runtime port.
- `pgvector` was also promoted into a dedicated hybrid migration: `alembic/versions/20260418_enable_pgvector_extension.py`
- `start.sh` crash-loop reset and cross-platform timestamp parsing were selected as safe startup ports.
- `schema v1` from `main` remains under review and should not be ported wholesale.
- `pyproject.toml`, `requirements.txt`, and `uv.lock` had no new runtime changes in `cc14d53`, so T012-T013 were effectively no-op.
