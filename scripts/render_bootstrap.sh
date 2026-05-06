#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

step() {
  printf '\n[%s/8] %s\n' "$1" "$2"
}

run_python() {
  uv run python "$@"
}

step 1 "Run Alembic migrations"
uv run alembic upgrade head

step 2 "Seed canonical product shell"
run_python scripts/seed.py

step 3 "Seed lecture runtime data"
run_python scripts/seed_lectures.py

step 4 "Import canonical artifacts Schema v2"
run_python -m src.scripts.pipeline.import_canonical_artifacts_to_db

step 5 "Backfill Schema v2"
run_python -m src.scripts.schema_v2.backfill_schema_v2 --apply --report-path reports/schema_v2_backfill_report.json

step 6 "Validate Schema v2"
run_python -m src.scripts.schema_v2.validate_schema_v2 --report-path reports/schema_v2_validation_report.json

step 7 "Check canonical runtime parity"
run_python -m src.scripts.pipeline.check_canonical_runtime_parity

step 8 "Create admin/demo accounts"
run_python -m src.scripts.create_seed_accounts

printf '\nRender bootstrap completed.\n'
