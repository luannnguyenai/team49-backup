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


def build_cleanup_readiness_report(
    *,
    targets: list[str],
    roots: list[Path],
    max_per_surface: int = 10,
) -> dict[str, Any]:
    target_report = validate_cleanup_targets(targets)
    usage_report = scan_legacy_usage(roots, max_per_surface=max_per_surface)
    blockers: list[str] = []

    if target_report["status"] != "ready":
        blockers.append("cleanup_targets_not_safe")
    if usage_report["status"] != "ready":
        blockers.append("runtime_legacy_references_remain")

    return {
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "target_report": target_report,
        "usage_report": usage_report,
        "required_next_steps": [] if not blockers else [
            "Do not run destructive rename/drop migrations.",
            "Migrate or guard remaining runtime legacy references.",
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
