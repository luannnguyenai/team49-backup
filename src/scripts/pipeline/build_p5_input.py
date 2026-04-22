"""Build Prompt 5 prerequisite-edge adjudication input from P2 output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ADJUDICATION_CONFIDENCE = {"low", "medium"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _course_ordering(p2_input_bundle: dict[str, Any] | None) -> dict[str, list[str]]:
    if not p2_input_bundle:
        return {}

    registry = p2_input_bundle.get("course_registry", {})
    courses = registry.get("courses", [])
    if not isinstance(courses, list):
        return {}

    ordering: dict[str, list[str]] = {}
    for course in courses:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        lecture_order = course.get("lecture_order")
        if isinstance(course_id, str) and isinstance(lecture_order, list):
            ordering[course_id] = [str(item) for item in lecture_order]
    return ordering


def build_p5_input(
    *,
    p2_output_path: Path,
    p2_input_bundle_path: Path | None,
    output_path: Path,
    run_id: str,
    p5_output_file_path: str,
) -> dict[str, Any]:
    p2_output = _load_json(p2_output_path)
    p2_input_bundle = _load_json(p2_input_bundle_path) if p2_input_bundle_path else None

    candidate_edges = p2_output.get("candidate_prerequisite_edges", [])
    if not isinstance(candidate_edges, list):
        raise ValueError("candidate_prerequisite_edges must be a list")

    edges_needing_adjudication: list[dict[str, Any]] = []
    bypassed_high_confidence_edges: list[dict[str, Any]] = []
    for edge in candidate_edges:
        if not isinstance(edge, dict):
            continue
        confidence = edge.get("candidate_confidence")
        if confidence in ADJUDICATION_CONFIDENCE:
            edges_needing_adjudication.append(edge)
        elif confidence == "high":
            bypassed_high_confidence_edges.append(edge)
        else:
            edges_needing_adjudication.append(edge)

    payload = {
        "run_id": run_id,
        "stage_id": "p5",
        "source_p2_file": str(p2_output_path),
        "source_p2_run_id": p2_output.get("run_id"),
        "source_p2_mode": p2_output.get("p2_mode"),
        "output_file_path": p5_output_file_path,
        "global_kps": p2_output.get("concepts_kp_global", []),
        "candidate_edges": edges_needing_adjudication,
        "bypassed_high_confidence_edges": bypassed_high_confidence_edges,
        "course_ordering": _course_ordering(p2_input_bundle),
        "unit_kp_map_global": p2_output.get("unit_kp_map_global", []),
        "input_stats": {
            "global_kps": len(p2_output.get("concepts_kp_global", [])),
            "candidate_edges_total": len(candidate_edges),
            "candidate_edges_for_adjudication": len(edges_needing_adjudication),
            "bypassed_high_confidence_edges": len(bypassed_high_confidence_edges),
            "unit_kp_map_global": len(p2_output.get("unit_kp_map_global", [])),
        },
    }

    _dump_json(output_path, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p2-output", type=Path, default=Path("data/p2_output_rationale_repaired.json"))
    parser.add_argument("--p2-input-bundle", type=Path, default=Path("data/p2_bundle/p2_input_bundle.json"))
    parser.add_argument("--output", type=Path, default=Path("data/p5_inputs/p5_input_cs224n_cs231n.json"))
    parser.add_argument("--run-id", default="p5_cs224n_cs231n")
    parser.add_argument(
        "--p5-output-file-path",
        default="data/p5_outputs/p5_adjudication_cs224n_cs231n.json",
    )
    args = parser.parse_args()

    payload = build_p5_input(
        p2_output_path=args.p2_output,
        p2_input_bundle_path=args.p2_input_bundle,
        output_path=args.output,
        run_id=args.run_id,
        p5_output_file_path=args.p5_output_file_path,
    )
    print(json.dumps({"output": str(args.output), "input_stats": payload["input_stats"]}, indent=2))


if __name__ == "__main__":
    main()
