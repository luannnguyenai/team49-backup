# Synthetic Demo Users Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic reset/import script for 9 demo accounts and a separate 30-user synthetic cohort.

**Architecture:** `src/scripts/pipeline/generate_synthetic_demo_users.py` owns pure fixture planning plus optional DB reset/import. Tests cover the pure fixture contract so the dataset shape, email domain, password hash, and no-random behavior stay stable.

**Tech Stack:** Python 3.12, SQLAlchemy async ORM, pytest, existing canonical/product DB models.

---

### Task 1: Document and Test Fixture Contract

**Files:**
- Create: `tests/pipeline/test_generate_synthetic_demo_users.py`
- Create: `src/scripts/pipeline/generate_synthetic_demo_users.py`

- [ ] Write failing tests for:
  - exactly 9 demo accounts and 30 cohort accounts
  - all emails end in `@vinuni.edu.vn`
  - demo password hash verifies `DemoPass123!`
  - cohort proficiency bands are distributed as 6 beginner, 7 developing, 10 proficient, 7 advanced
  - demo/cohort datasets are distinct
  - fixture build is deterministic across repeated calls

- [ ] Run the test and verify it fails because the script does not exist.

- [ ] Implement the pure fixture definitions and deterministic helper functions.

- [ ] Run the test and verify it passes.

### Task 2: Add DB Reset/Import and JSONL Snapshot Output

**Files:**
- Modify: `src/scripts/pipeline/generate_synthetic_demo_users.py`
- Test: `tests/pipeline/test_generate_synthetic_demo_users.py`

- [ ] Add deterministic catalog selection from `courses`, `course_sections`, `learning_units`, `question_bank`, `item_phase_map`, and `item_kp_map`.
- [ ] Add JSONL snapshot writing under `data/synthetic/<dataset>/`.
- [ ] Add async DB import that deletes known synthetic users by email and recreates user, goal, session, interaction, mastery, progress, waive, planner, and rationale rows.
- [ ] Add tests for CLI argument parsing and snapshot path planning without requiring a live DB.
- [ ] Run targeted tests.

### Task 3: Update Docs and Verify

**Files:**
- Modify: `THINGS NEED FIX.md`
- Modify: `docs/WORKLOG.md`
- Modify: `docs/PRODUCTION_DB_INTEGRATION_HANDOFF.md`

- [ ] Document the synthetic demo reset command and account list.
- [ ] Confirm synthetic remains separate from real calibration readiness.
- [ ] Run targeted tests, compile check, and diff check.
- [ ] Commit the completed work.
