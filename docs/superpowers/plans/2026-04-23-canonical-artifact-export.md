# Canonical Artifact Export Implementation Plan

> **Historical plan:** This document is preserved for implementation history only. Canonical export has already been implemented; use the current exporter code and handoff docs for active behavior.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export a self-contained canonical artifact bundle for courses, concepts, units, unit-KP mappings, question-layer tables, and prerequisite edges, with deterministic validation and manifest metadata.

**Architecture:** Add a dedicated exporter that reads canonical sources from P1/P2/P4/P5 artifacts, normalizes them into JSONL tables under `data/final_artifacts/cs224n_cs231n_v1/canonical/`, and emits a validation report split into blocking hard checks and deferred checks. Reuse existing path constants and as much extraction logic as possible from the older final-bundle exporter, but keep this exporter DB-independent and contract-focused.

**Tech Stack:** Python 3.12, standard library JSON/Pathlib/hashlib, existing repo data artifacts, no DB access.

---

### Task 1: Update the spec and align output contract

**Files:**
- Modify: `docs/superpowers/specs/2026-04-23-artifact-first-canonical-export-design.md`

- [ ] **Step 1: Verify the spec reflects Tier 1 and Tier 2 contract changes**

Run: `rg -n "courses.jsonl|concepts_kp.jsonl|unit_kp_map.jsonl|mastery_mean_cached|source_ref|edge_scope|hard_checks|deferred_checks" docs/superpowers/specs/2026-04-23-artifact-first-canonical-export-design.md`

Expected: all new contract pieces are present, and `mastery_mean_cached` is absent.

- [ ] **Step 2: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-04-23-artifact-first-canonical-export-design.md
git commit -m "docs: refine canonical artifact export contract"
```

- [ ] **Step 3: Decide generated artifact versioning policy**

Policy for this implementation:
- do **not** commit canonical generated JSONL files
- do commit code/docs
- only inspect/generated `manifest.json` and `validation_report.json` locally unless explicitly asked to version them

Run: `rg -n "Git strategy|rejected_items.jsonl|checksums|canonical.tmp" docs/superpowers/specs/2026-04-23-artifact-first-canonical-export-design.md`

Expected: spec contains the agreed versioning and write-safety policy.

### Task 2: Build the canonical exporter

**Files:**
- Create: `src/scripts/pipeline/export_canonical_artifacts.py`
- Modify: `src/data_paths.py`
- Reference: `src/scripts/pipeline/export_final_ingest_bundle.py`

- [ ] **Step 1: Add canonical output path constants**

Add constants in `src/data_paths.py` for:
- canonical output directory
- canonical manifest path
- canonical validation report path

- [ ] **Step 2: Write the failing smoke command**

Run: `python src/scripts/pipeline/export_canonical_artifacts.py`

Expected: fail initially because file/function does not yet exist.

- [ ] **Step 3a: Implement source loaders**

The exporter must load:
- `courses/*/syllabus.json`
- `courses/*/processed_sanitized/L*_p1.json`
- `data/final_artifacts/cs224n_cs231n_v1/p2_output_rationale_repaired.json`
- `courses/*/processed/P4/**/*.json`
- `p5_output_transitive_pruned.json`
- `gpt54_edge_labels.json`

and centralize transcript resolution so evidence-span checks can run against real transcript files.

- [ ] **Step 3b: Implement canonical emitters for metadata/content graph**

Emit:
- `courses.jsonl`
- `concepts_kp.jsonl`
- `units.jsonl`
- `unit_kp_map.jsonl`

- [ ] **Step 3c: Implement canonical emitters for question layer**

Emit:
- `question_bank.jsonl`
- `item_calibration.jsonl`
- `item_phase_map.jsonl`
- `item_kp_map.jsonl`

with rule-based default fill for `item_kp_map.weight`.

- [ ] **Step 3d: Implement canonical emitters for prerequisite graph**

Emit:
- `prerequisite_edges.jsonl`
- `pruned_edges.jsonl`

using final edge verdicts from canonical `gpt54_edge_labels.json`.

- [ ] **Step 3e: Implement manifest writer and atomic output directory swap**

The exporter must write to `canonical.tmp/`, validate there, then atomically replace `canonical/`.

- [ ] **Step 3f: Commit the exporter skeleton**

```bash
git add src/data_paths.py src/scripts/pipeline/export_canonical_artifacts.py
git commit -m "feat: scaffold canonical artifact exporter"
```

### Task 2.5: Add a fixture smoke test before running on full data

**Files:**
- Create: `tests/pipeline/test_export_canonical_artifacts.py`

- [ ] **Step 1: Write a smoke test around a tiny fixture bundle**

The test should exercise:
- at least 1 course
- at least 1 lecture
- at least 2 units
- at least 1 question item
- at least 1 edge

and assert the exporter emits the expected canonical files and minimal manifest counts.

- [ ] **Step 2: Run the smoke test**

Run: `pytest tests/pipeline/test_export_canonical_artifacts.py -q`

Expected: PASS.

- [ ] **Step 3: Commit the smoke test**

```bash
git add tests/pipeline/test_export_canonical_artifacts.py
git commit -m "test: add canonical artifact exporter smoke test"
```

- [ ] **Step 4: Run the exporter on full data**

Run: `PYTHONPATH=. python src/scripts/pipeline/export_canonical_artifacts.py`

Expected: all canonical files are created under `data/final_artifacts/cs224n_cs231n_v1/canonical/`.

- [ ] **Step 5: Commit exporter fixes only if the full-data run required code changes**

If Step 4 exposed real bugs and you changed exporter code after the skeleton commit, then commit:

```bash
git add src/data_paths.py src/scripts/pipeline/export_canonical_artifacts.py tests/pipeline/test_export_canonical_artifacts.py
git commit -m "fix: stabilize canonical artifact exporter on full dataset"
```

### Task 3: Add deterministic validation and hard-fail handling

**Files:**
- Modify: `src/scripts/pipeline/export_canonical_artifacts.py`
- Create: `tests/pipeline/test_export_canonical_validation.py`

- [ ] **Step 1: Encode blocking hard checks**

Implement checks for:
- referential integrity across canonical tables
- duplicate IDs / duplicate key pairs
- enum membership for phase / provenance / review_status
- source_ref existence
- evidence span substring matching where transcript source is available
- timestamp bounds against `content_ref`
- hard-fail routing to `rejected_items.jsonl`

- [ ] **Step 1.5: Add validator tests for hard-check families**

Add focused tests covering at least one failing example for each family:
- referential integrity
- duplicate keys
- enum membership
- source_ref presence
- evidence_span substring matching
- timestamp bounds

Run: `pytest tests/pipeline/test_export_canonical_validation.py -q`

Expected: PASS.

- [ ] **Step 2: Encode deferred checks**

Log but do not fail on:
- missing cosine metrics
- missing ML edge scores
- any embedding-dependent checks intentionally deferred

- [ ] **Step 3: Add checksums to manifest**

Compute `sha256` for every canonical file plus `validation_report.json`.

- [ ] **Step 4: Re-run exporter and inspect validation report**

Run: `PYTHONPATH=. python src/scripts/pipeline/export_canonical_artifacts.py`

Expected: `validation_report.json` includes `hard_checks` and `deferred_checks` sections, with no unexpected hard failures, and manifest includes file checksums.

- [ ] **Step 5: Commit validation logic**

```bash
git add src/scripts/pipeline/export_canonical_artifacts.py
git commit -m "feat: add canonical artifact validation report"
```

### Task 4: Verify output counts and contract shape

**Files:**
- Verify: `data/final_artifacts/cs224n_cs231n_v1/canonical/*.jsonl`
- Verify: `data/final_artifacts/cs224n_cs231n_v1/canonical/manifest.json`
- Verify: `data/final_artifacts/cs224n_cs231n_v1/canonical/validation_report.json`
- Verify: `data/final_artifacts/cs224n_cs231n_v1/canonical/rejected_items.jsonl`

- [ ] **Step 1: Check core counts**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path("data/final_artifacts/cs224n_cs231n_v1/canonical")
manifest = json.loads((root / "manifest.json").read_text())
report = json.loads((root / "validation_report.json").read_text())
print(json.dumps(manifest["counts"], indent=2))
print(json.dumps(report["summary"], indent=2))
PY
```

Expected:
- all expected tables present
- counts non-zero for courses/concepts/units/question_bank/prerequisite_edges
- validation summary indicates no blocking failures

- [ ] **Step 2: Check JSONL line counts against manifest**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path("data/final_artifacts/cs224n_cs231n_v1/canonical")
manifest = json.loads((root / "manifest.json").read_text())
for name, count in manifest["counts"].items():
    path = root / f"{name}.jsonl"
    if path.exists():
        actual = sum(1 for _ in path.open(encoding="utf-8"))
        print(name, count, actual)
PY
```

Expected: every JSONL line count matches manifest count.

- [ ] **Step 3: Do not commit generated canonical JSONL**

This implementation intentionally leaves generated JSONL uncommitted. Only review them locally.

- [ ] **Step 4: If needed, commit tiny metadata snapshots only**

```bash
git add docs/WORKLOG.md docs/JOURNAL.md
git commit -m "docs: record canonical artifact export verification"
```

### Task 5: Document how the canonical bundle should be used next

**Files:**
- Modify: `docs/WORKLOG.md`
- Modify: `docs/JOURNAL.md`

- [ ] **Step 1: Record the new canonical export phase**

Add a short entry describing:
- artifact-first export complete
- canonical output location
- validation report purpose
- importer/DB ingest deferred to next phase

- [ ] **Step 2: Commit the docs**

```bash
git add docs/WORKLOG.md docs/JOURNAL.md
git commit -m "docs: record canonical artifact export phase"
```
