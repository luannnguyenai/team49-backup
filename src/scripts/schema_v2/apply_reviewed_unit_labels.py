from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.scripts.schema_v2.backfill_schema_v2 import sha256_json


DEFAULT_CANONICAL_DIR = Path("data/final_artifacts/cs224n_cs231n_cs230_v1/canonical")
DEFAULT_LABELS_FILE = DEFAULT_CANONICAL_DIR / "schema_v2_reviewed_unit_labels.jsonl"

UNIT_FIELDS = {
    "content_type",
    "content_type_confidence",
    "is_worth_learning",
    "salience_score",
    "salience_confidence",
    "has_quiz_items",
    "override_critical_kp",
    "active",
    "deprecated_at",
    "deprecated_reason",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _unit_hash(unit: dict[str, Any]) -> str:
    return sha256_json(
        {
            "unit_id": unit.get("unit_id"),
            "course_id": unit.get("course_id"),
            "lecture_id": unit.get("lecture_id"),
            "unit_name": unit.get("unit_name"),
            "summary": unit.get("summary"),
            "content_ref": unit.get("content_ref"),
            "key_points": unit.get("key_points"),
            "transcript_path": unit.get("transcript_path"),
            "video_clip_ref": unit.get("video_clip_ref"),
        }
    )


def apply_labels(input_dir: Path, labels_file: Path) -> dict[str, Any]:
    units_path = input_dir / "units.jsonl"
    units = _read_jsonl(units_path)
    labels = _read_jsonl(labels_file)

    labels_by_unit = {row["unit_id"]: row for row in labels}
    missing_units = sorted(set(labels_by_unit) - {row["unit_id"] for row in units})
    if missing_units:
        raise ValueError(f"Labels reference unknown unit_id values: {missing_units[:10]}")

    applied = 0
    for unit in units:
        label = labels_by_unit.get(unit["unit_id"])
        if not label:
            continue
        for field in UNIT_FIELDS:
            if field in label:
                unit[field] = label[field]
        unit["content_hash"] = _unit_hash(unit)
        applied += 1

    _write_jsonl(units_path, units)
    return {
        "labels_file": str(labels_file),
        "units_file": str(units_path),
        "label_count": len(labels),
        "applied_count": applied,
        "unlabeled_units": len(units) - applied,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply reviewed Schema v2 unit labels to canonical units.jsonl.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_CANONICAL_DIR)
    parser.add_argument("--labels-file", type=Path, default=DEFAULT_LABELS_FILE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = apply_labels(args.input_dir, args.labels_file)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
