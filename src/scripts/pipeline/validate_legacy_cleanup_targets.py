from __future__ import annotations

import argparse
import json
import sys
from typing import Any


LEGACY_CLEANUP_ALLOWLIST: frozenset[str] = frozenset(
    {
        "modules",
        "topics",
        "knowledge_components",
        "questions",
        "mastery_scores",
        "mastery_history",
        "learning_paths",
    }
)

PROTECTED_TABLES: frozenset[str] = frozenset(
    {
        "concepts_kp",
        "units",
        "unit_kp_map",
        "question_bank",
        "item_calibration",
        "item_phase_map",
        "item_kp_map",
        "prerequisite_edges",
        "pruned_edges",
        "learner_mastery_kp",
        "goal_preferences",
        "waived_units",
        "plan_history",
        "rationale_log",
        "planner_session_state",
        "courses",
        "course_sections",
        "learning_units",
        "course_assets",
        "course_overviews",
        "learning_progress_records",
        "sessions",
        "interactions",
        "users",
    }
)


def validate_cleanup_targets(targets: list[str]) -> dict[str, Any]:
    normalized = sorted({target.strip() for target in targets if target.strip()})
    protected_hits = sorted(set(normalized) & PROTECTED_TABLES)
    unsupported = sorted(set(normalized) - LEGACY_CLEANUP_ALLOWLIST)
    allowed = sorted(set(normalized) & LEGACY_CLEANUP_ALLOWLIST)
    status = "ready" if normalized and not protected_hits and not unsupported else "blocked"
    return {
        "status": status,
        "targets": normalized,
        "allowed_targets": allowed,
        "unsupported_targets": unsupported,
        "protected_hits": protected_hits,
        "legacy_cleanup_allowlist": sorted(LEGACY_CLEANUP_ALLOWLIST),
        "protected_tables": sorted(PROTECTED_TABLES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight guard for destructive legacy cleanup targets."
    )
    parser.add_argument(
        "targets",
        nargs="+",
        help="Table names intended for legacy cleanup migration.",
    )
    args = parser.parse_args()

    report = validate_cleanup_targets(args.targets)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
