from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.scripts.pipeline.check_legacy_schema_usage import scan_legacy_usage
from src.scripts.pipeline.validate_legacy_cleanup_targets import (
    LEGACY_CLEANUP_ALLOWLIST,
    validate_cleanup_targets,
)

GUARDED_COMPATIBILITY_PATHS: dict[str, str] = {
    "src/kg/": "allow_legacy_kg_routes",
    "src/routers/content.py": "allow_legacy_topic_content_reads",
    "src/services/content_service.py": "allow_legacy_topic_content_reads",
    "src/services/quiz_service.py": "allow_legacy_question_reads/allow_legacy_mastery_writes/allow_legacy_planner_writes",
    "src/services/module_test_service.py": "allow_legacy_question_reads/allow_legacy_mastery_writes/allow_legacy_planner_writes",
    "src/services/recommendation_engine.py": "allow_legacy_planner_writes/read_canonical_planner_enabled",
}

ACCEPTED_LEGACY_DEFINITION_PATHS: frozenset[str] = frozenset(
    {
        "src/models/content.py",
        "src/models/learning.py",
        "src/models/__init__.py",
    }
)


def _guard_for_reference(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    marker = "/src/"
    if marker in normalized:
        normalized = "src/" + normalized.split(marker, 1)[1]
    for prefix, guard in GUARDED_COMPATIBILITY_PATHS.items():
        if normalized.startswith(prefix):
            return guard
    return None


def _is_accepted_definition_reference(path: str) -> bool:
    normalized = path.replace("\\", "/")
    marker = "/src/"
    if marker in normalized:
        normalized = "src/" + normalized.split(marker, 1)[1]
    return normalized in ACCEPTED_LEGACY_DEFINITION_PATHS


def classify_usage_references(usage_report: dict[str, Any]) -> dict[str, Any]:
    guarded: list[dict[str, Any]] = []
    accepted_definitions: list[dict[str, Any]] = []
    unguarded: list[dict[str, Any]] = []

    for surface in usage_report["surfaces"]:
        for ref in surface["references"]:
            item = {
                "table": surface["table"],
                "path": ref["path"],
                "line": ref["line"],
                "text": ref["text"],
            }
            guard = _guard_for_reference(ref["path"])
            if guard is not None:
                item["guard"] = guard
                guarded.append(item)
            elif _is_accepted_definition_reference(ref["path"]):
                accepted_definitions.append(item)
            else:
                unguarded.append(item)

    return {
        "guarded_reference_examples": guarded,
        "accepted_definition_examples": accepted_definitions,
        "unguarded_reference_examples": unguarded,
        "guarded_example_count": len(guarded),
        "accepted_definition_example_count": len(accepted_definitions),
        "unguarded_example_count": len(unguarded),
    }


def build_cleanup_readiness_report(
    *,
    targets: list[str],
    roots: list[Path],
    max_per_surface: int = 10,
) -> dict[str, Any]:
    target_report = validate_cleanup_targets(targets)
    usage_report = scan_legacy_usage(roots, max_per_surface=max_per_surface)
    usage_classification = classify_usage_references(usage_report)
    blockers: list[str] = []

    if target_report["status"] != "ready":
        blockers.append("cleanup_targets_not_safe")
    if usage_classification["unguarded_example_count"] > 0:
        blockers.append("unguarded_runtime_legacy_references_remain")

    return {
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "target_report": target_report,
        "usage_report": usage_report,
        "usage_classification": usage_classification,
        "required_next_steps": [] if not blockers else [
            "Do not run destructive rename/drop migrations.",
            "Migrate or guard remaining unguarded runtime legacy references.",
            "Run archive exporter and parity checks before retrying.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether legacy schema cleanup can proceed.")
    parser.add_argument(
        "--root",
        action="append",
        default=None,
        help="Runtime source root to scan. Defaults to src.",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=None,
        help="Legacy cleanup target table. Defaults to the full legacy cleanup allowlist.",
    )
    parser.add_argument(
        "--max-per-surface",
        type=int,
        default=10,
        help="Maximum usage references to include per legacy surface.",
    )
    args = parser.parse_args()

    roots = [Path(root) for root in (args.root or ["src"])]
    targets = list(args.target or sorted(LEGACY_CLEANUP_ALLOWLIST))
    report = build_cleanup_readiness_report(
        targets=targets,
        roots=roots,
        max_per_surface=args.max_per_surface,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
