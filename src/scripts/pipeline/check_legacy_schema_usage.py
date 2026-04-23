from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LegacySurface:
    table: str
    status: str
    replacement: str
    patterns: tuple[str, ...]


LEGACY_SURFACES: tuple[LegacySurface, ...] = (
    LegacySurface(
        table="modules",
        status="deprecated",
        replacement="courses/course_sections/learning_units",
        patterns=(r"\bModule\b", r"\bmodules\b", r"['\"]modules['\"]"),
    ),
    LegacySurface(
        table="topics",
        status="deprecated",
        replacement="learning_units/units/unit_kp_map",
        patterns=(r"\bTopic\b", r"\btopics\b", r"['\"]topics['\"]"),
    ),
    LegacySurface(
        table="knowledge_components",
        status="deprecated",
        replacement="concepts_kp/unit_kp_map/item_kp_map",
        patterns=(r"\bKnowledgeComponent\b", r"\bknowledge_components\b", r"['\"]knowledge_components['\"]"),
    ),
    LegacySurface(
        table="questions",
        status="deprecated",
        replacement="question_bank/item_calibration/item_phase_map/item_kp_map",
        patterns=(r"\bQuestion\b", r"\bquestions\b", r"['\"]questions['\"]"),
    ),
    LegacySurface(
        table="mastery_scores",
        status="deprecated",
        replacement="learner_mastery_kp",
        patterns=(r"\bMasteryScore\b", r"\bmastery_scores\b", r"['\"]mastery_scores['\"]"),
    ),
    LegacySurface(
        table="mastery_history",
        status="deprecated",
        replacement="future KP mastery audit",
        patterns=(r"\bMasteryHistory\b", r"\bmastery_history\b", r"['\"]mastery_history['\"]"),
    ),
    LegacySurface(
        table="learning_paths",
        status="deprecated",
        replacement="plan_history/rationale_log/canonical planner output",
        patterns=(r"\bLearningPath\b", r"\blearning_paths\b", r"['\"]learning_paths['\"]"),
    ),
)

DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "alembic",
    "docs",
    "data",
    "frontend",
    "node_modules",
    "scripts",
}


def _compile_surface_pattern(surface: LegacySurface) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{pattern})" for pattern in surface.patterns))


def _should_skip(path: Path, *, roots: tuple[Path, ...], excluded_parts: set[str]) -> bool:
    if path.name == "check_legacy_schema_usage.py":
        return True
    if path.name == "config.py":
        return True
    if path.suffix != ".py":
        return True
    try:
        relative_parts = next(path.relative_to(root).parts for root in roots if path.is_relative_to(root))
    except StopIteration:
        relative_parts = path.parts
    return bool(set(relative_parts) & excluded_parts)


def iter_python_files(roots: list[Path], *, excluded_parts: set[str] | None = None) -> list[Path]:
    excluded = excluded_parts or DEFAULT_EXCLUDED_PARTS
    resolved_roots = tuple(root.resolve() for root in roots)
    files: list[Path] = []
    for root in resolved_roots:
        if root.is_file():
            if not _should_skip(root, roots=resolved_roots, excluded_parts=excluded):
                files.append(root)
            continue
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if not _should_skip(path, roots=resolved_roots, excluded_parts=excluded):
                files.append(path)
    return sorted(files)


def scan_legacy_usage(
    roots: list[Path],
    *,
    max_per_surface: int = 25,
    excluded_parts: set[str] | None = None,
) -> dict[str, Any]:
    files = iter_python_files(roots, excluded_parts=excluded_parts)
    compiled = {surface.table: _compile_surface_pattern(surface) for surface in LEGACY_SURFACES}
    results: list[dict[str, Any]] = []

    for surface in LEGACY_SURFACES:
        references: list[dict[str, Any]] = []
        total = 0
        pattern = compiled[surface.table]
        for path in files:
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if not pattern.search(line):
                    continue
                total += 1
                if len(references) < max_per_surface:
                    references.append(
                        {
                            "path": str(path),
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )
        results.append(
            {
                "table": surface.table,
                "status": surface.status,
                "replacement": surface.replacement,
                "reference_count": total,
                "truncated": total > len(references),
                "references": references,
            }
        )

    deprecated_reference_count = sum(
        surface["reference_count"] for surface in results if surface["status"] == "deprecated"
    )
    return {
        "status": "blocked" if deprecated_reference_count else "ready",
        "deprecated_reference_count": deprecated_reference_count,
        "roots": [str(root) for root in roots],
        "surfaces": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan source files for legacy schema references.")
    parser.add_argument(
        "roots",
        nargs="*",
        default=["src"],
        help="Files or directories to scan. Defaults to src.",
    )
    parser.add_argument(
        "--max-per-surface",
        type=int,
        default=25,
        help="Maximum references to include per legacy surface.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when deprecated references remain.",
    )
    args = parser.parse_args()

    report = scan_legacy_usage(
        [Path(root) for root in args.roots],
        max_per_surface=args.max_per_surface,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["deprecated_reference_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
