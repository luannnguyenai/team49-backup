"""Export canonical final ingest artifacts from prompt pipeline outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _iter_json_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _load_p1_units(course_id: str, sanitized_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(sanitized_dir.glob("L*_p1.json")):
        artifact = _load_json(path)
        lecture_id = artifact.get("lecture_id") or path.stem.removesuffix("_p1")
        for unit in artifact.get("units", []):
            if not isinstance(unit, dict):
                continue
            row = dict(unit)
            row["course_id"] = course_id
            row["lecture_id"] = lecture_id
            row["source_p1_file"] = str(path)
            rows.append(row)
    return rows


def _p4_rows(course_id: str, p4_root: Path) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    question_rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    phase_rows: list[dict[str, Any]] = []
    skipped_unit_rows: list[dict[str, Any]] = []

    for path in _iter_json_files(p4_root):
        artifact = _load_json(path)
        unit_id = artifact.get("unit_id")
        bank = artifact.get("repaired_question_bank", [])
        if not bank:
            skipped_unit_rows.append(
                {
                    "course_id": course_id,
                    "unit_id": unit_id,
                    "source_p4_file": str(path),
                    "target_item_count": artifact.get("target_item_count"),
                    "review_summary": artifact.get("review_summary"),
                }
            )
            continue

        calibration_by_item = {
            row.get("item_id"): row
            for row in artifact.get("item_calibration_bootstrap", [])
            if isinstance(row, dict) and row.get("item_id")
        }
        phases_by_item = {
            row.get("item_id"): row
            for row in artifact.get("item_phase_map", [])
            if isinstance(row, dict) and row.get("item_id")
        }

        for item in bank:
            if not isinstance(item, dict):
                continue
            item_id = item.get("item_id")
            question_rows.append(
                {
                    "course_id": course_id,
                    "unit_id": unit_id,
                    "source_p4_file": str(path),
                    **item,
                }
            )
            if item_id in calibration_by_item:
                calibration_rows.append(
                    {
                        "course_id": course_id,
                        "unit_id": unit_id,
                        "source_p4_file": str(path),
                        **calibration_by_item[item_id],
                    }
                )
            if item_id in phases_by_item:
                phase_rows.append(
                    {
                        "course_id": course_id,
                        "unit_id": unit_id,
                        "source_p4_file": str(path),
                        **phases_by_item[item_id],
                    }
                )

    return question_rows, calibration_rows, phase_rows, skipped_unit_rows


def _final_edges(p5: dict[str, Any], gpt54: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    labels = {}
    if gpt54:
        labels = {
            (row["source_kp_id"], row["target_kp_id"]): row
            for row in gpt54.get("edge_labels", [])
            if isinstance(row, dict) and row.get("source_kp_id") and row.get("target_kp_id")
        }

    clean_edges: list[dict[str, Any]] = []
    pruned_edges = list(p5.get("pruned_edges", []))
    for edge in p5.get("clean_candidate_edges", []):
        pair = (edge.get("source_kp_id"), edge.get("target_kp_id"))
        label = labels.get(pair)
        if label and label.get("gpt54_verdict") == "prune":
            pruned_edges.append(
                {
                    "source_kp_id": edge.get("source_kp_id"),
                    "target_kp_id": edge.get("target_kp_id"),
                    "prune_reason": label.get("suggested_prune_reason", "weak_cooccurrence"),
                    "prune_rationale": label.get("gpt54_rationale"),
                    "provenance": "gpt54_audit",
                    "source_p5_keep_confidence": edge.get("keep_confidence"),
                    "source_p5_provenance": edge.get("provenance"),
                }
            )
            continue
        row = dict(edge)
        if label:
            row["gpt54_audit"] = {
                "verdict": label.get("gpt54_verdict"),
                "confidence": label.get("gpt54_confidence"),
                "rationale": label.get("gpt54_rationale"),
                "suggested_review_status": label.get("suggested_review_status"),
            }
        clean_edges.append(row)

    return clean_edges, pruned_edges


def export_bundle(
    *,
    output_dir: Path,
    p2_path: Path,
    p5_path: Path,
    gpt54_path: Path | None,
    courses: list[str],
) -> dict[str, Any]:
    p2 = _load_json(p2_path)
    p5 = _load_json(p5_path)
    gpt54 = _load_json(gpt54_path) if gpt54_path and gpt54_path.exists() else None

    units: list[dict[str, Any]] = []
    question_bank: list[dict[str, Any]] = []
    item_calibration: list[dict[str, Any]] = []
    item_phase_map: list[dict[str, Any]] = []
    skipped_units: list[dict[str, Any]] = []

    for course_id in courses:
        course_root = Path("data") / course_id
        units.extend(_load_p1_units(course_id, course_root / "processed_sanitized"))
        q_rows, c_rows, p_rows, s_rows = _p4_rows(course_id, course_root / "processed" / "P4")
        question_bank.extend(q_rows)
        item_calibration.extend(c_rows)
        item_phase_map.extend(p_rows)
        skipped_units.extend(s_rows)

    prerequisite_edges, pruned_edges = _final_edges(p5, gpt54)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "lectures_units.jsonl", units)
    _write_jsonl(output_dir / "concepts_kp_global.jsonl", p2.get("concepts_kp_global", []))
    _write_jsonl(output_dir / "local_to_global_map.jsonl", p2.get("local_to_global_map", []))
    _write_jsonl(output_dir / "unit_kp_map_global.jsonl", p2.get("unit_kp_map_global", []))
    _write_jsonl(output_dir / "question_bank.jsonl", question_bank)
    _write_jsonl(output_dir / "item_calibration.jsonl", item_calibration)
    _write_jsonl(output_dir / "item_phase_map.jsonl", item_phase_map)
    _write_jsonl(output_dir / "skipped_units.jsonl", skipped_units)
    _write_jsonl(output_dir / "prerequisite_edges.jsonl", prerequisite_edges)
    _write_jsonl(output_dir / "pruned_edges.jsonl", pruned_edges)

    manifest = {
        "bundle_id": output_dir.name,
        "created_at": datetime.now(UTC).isoformat(),
        "courses": courses,
        "source_files": {
            "p2": str(p2_path),
            "p5": str(p5_path),
            "gpt54_edge_labels": str(gpt54_path) if gpt54_path else None,
        },
        "counts": {
            "lectures_units": len(units),
            "concepts_kp_global": len(p2.get("concepts_kp_global", [])),
            "local_to_global_map": len(p2.get("local_to_global_map", [])),
            "unit_kp_map_global": len(p2.get("unit_kp_map_global", [])),
            "question_bank": len(question_bank),
            "item_calibration": len(item_calibration),
            "item_phase_map": len(item_phase_map),
            "skipped_units": len(skipped_units),
            "prerequisite_edges": len(prerequisite_edges),
            "pruned_edges": len(pruned_edges),
        },
        "notes": [
            "P3 artifacts are intentionally excluded from final ingest bundle.",
            "ModernBERT/SciBERT experiment scores are intentionally excluded from final ingest decisions.",
            "prerequisite_edges apply GPT-5.4 audit prune suggestions on top of P5 transitive-pruned output.",
        ],
    }
    manifest["validation"] = {
        "question_calibration_count_match": len(question_bank) == len(item_calibration),
        "question_phase_count_match": len(question_bank) == len(item_phase_map),
        "edge_count_source": {
            "p5_clean": len(p5.get("clean_candidate_edges", [])),
            "gpt54_prune_suggestions_applied": len(p5.get("clean_candidate_edges", [])) - len(prerequisite_edges),
        },
        "question_item_type_distribution": dict(Counter(row.get("item_type") for row in question_bank)),
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/final/cs224n_cs231n_v1"))
    parser.add_argument("--p2", type=Path, default=Path("data/p2_output_rationale_repaired.json"))
    parser.add_argument("--p5", type=Path, default=Path("data/p5_output_transitive_pruned.json"))
    parser.add_argument("--gpt54", type=Path, default=Path("data/gpt54_edge_labels.json"))
    parser.add_argument("--courses", nargs="+", default=["CS224n", "CS231n"])
    args = parser.parse_args()

    manifest = export_bundle(
        output_dir=args.output_dir,
        p2_path=args.p2,
        p5_path=args.p5,
        gpt54_path=args.gpt54,
        courses=args.courses,
    )
    print(json.dumps(manifest["counts"], indent=2))
    print(json.dumps(manifest["validation"], indent=2))


if __name__ == "__main__":
    main()
