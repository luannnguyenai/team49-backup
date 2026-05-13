from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data_paths import COURSES_FILE, OVERVIEWS_FILE
from src.scripts.pipeline.import_canonical_artifacts_to_db import IMPORT_SPECS, load_jsonl
from scripts.seed_lectures import _course_specs


def _ensure_file(path: Path, *, label: str) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    if not path.is_file():
        raise ValueError(f"Expected {label} to be a file: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError(f"{label} is empty: {path}")
    return {"path": str(path), "bytes": size}


def assert_canonical_bundle(canonical_dir: Path) -> dict[str, object]:
    report: dict[str, object] = {
        "manifest": _ensure_file(canonical_dir / "manifest.json", label="canonical manifest"),
    }
    files: dict[str, object] = {}
    for table_name, spec in IMPORT_SPECS.items():
        files[table_name] = _ensure_file(canonical_dir / spec.filename, label=f"canonical {spec.filename}")
    report["tables"] = files
    return report


def assert_bootstrap_metadata() -> dict[str, object]:
    return {
        "courses": _ensure_file(COURSES_FILE, label="bootstrap courses.json"),
        "overviews": _ensure_file(OVERVIEWS_FILE, label="bootstrap overviews.json"),
    }


def assert_runtime_lecture_inputs(canonical_dir: Path) -> dict[str, object]:
    report: dict[str, object] = {}
    course_dirs = dict(_course_specs())
    canonical_units = load_jsonl(canonical_dir / IMPORT_SPECS["units"].filename)
    grouped: dict[str, dict[int, str]] = {}

    for row in canonical_units:
        course_id = row.get("course_id")
        lecture_order = row.get("lecture_order")
        transcript_path = row.get("transcript_path")
        if not isinstance(course_id, str) or not isinstance(lecture_order, int):
            continue
        course_slug = course_id.strip().lower()
        if course_slug not in course_dirs:
            continue
        if not isinstance(transcript_path, str) or not transcript_path.strip():
            raise ValueError(
                f"Missing transcript_path for {course_slug} lecture {lecture_order} in canonical units"
            )
        existing_path = grouped.setdefault(course_slug, {}).get(lecture_order)
        if existing_path is not None and existing_path != transcript_path:
            raise ValueError(
                f"Inconsistent transcript_path for {course_slug} lecture {lecture_order}: "
                f"{existing_path} != {transcript_path}"
            )
        grouped[course_slug][lecture_order] = transcript_path

    for course_slug, transcripts_by_lecture in grouped.items():
        if not transcripts_by_lecture:
            continue
        transcript_reports: list[dict[str, object]] = []
        for lecture_order, transcript_path in sorted(transcripts_by_lecture.items()):
            transcript_reports.append(
                {
                    "lecture_order": lecture_order,
                    **_ensure_file(
                        Path(transcript_path),
                        label=f"{course_slug} transcript for lecture {lecture_order}",
                    ),
                }
            )
        report[course_slug] = {
            "lecture_count": len(transcripts_by_lecture),
            "transcripts": transcript_reports,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-fast validation for ECS init data sources from S3 bundle and image-baked files."
    )
    parser.add_argument("--canonical-dir", type=Path, required=True)
    parser.add_argument("--require-bootstrap", action="store_true")
    parser.add_argument("--require-runtime-lecture-inputs", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "canonical_bundle": assert_canonical_bundle(args.canonical_dir),
    }
    if args.require_bootstrap:
        report["bootstrap"] = assert_bootstrap_metadata()
    if args.require_runtime_lecture_inputs:
        report["runtime_lecture_inputs"] = assert_runtime_lecture_inputs(args.canonical_dir)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
