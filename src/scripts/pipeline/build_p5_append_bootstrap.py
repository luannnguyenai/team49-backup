"""Build append-mode P5 artifacts from new P2 candidate edges.

This script preserves an existing P5 adjudication artifact and appends new P2
candidate edges with `rule_based` provenance. It is intended as a deterministic
bootstrap when the new course has already been manually reviewed enough to move
forward, but before a full 3-role LLM P5 re-adjudication is run.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _edge_pair(row: dict[str, Any]) -> tuple[str, str]:
    return row["source_kp_id"], row["target_kp_id"]


def _new_source_kps(p2_output: dict[str, Any], new_course_id: str) -> set[str]:
    output: set[str] = set()
    for row in p2_output.get("concepts_kp_global", []):
        if new_course_id in (row.get("source_course_ids") or []):
            output.add(row["global_kp_id"])
    return output


def _candidate_to_clean_edge(row: dict[str, Any]) -> dict[str, Any]:
    confidence = row.get("candidate_confidence") or "medium"
    return {
        "source_kp_id": row["source_kp_id"],
        "target_kp_id": row["target_kp_id"],
        "edge_scope": row.get("edge_scope"),
        "provenance": "rule_based",
        "keep_confidence": confidence,
        "keep_rationale": row.get("candidate_rationale")
        or "Kept by deterministic append bootstrap from P2 candidate prerequisite edge.",
        "expected_directionality": "strong" if confidence == "high" else "moderate",
        "review_status": "optional" if confidence == "medium" else "not_required",
        "ready_for_modernbert": True,
    }


def _dedupe_candidate_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        pair = _edge_pair(row)
        existing = by_pair.get(pair)
        if existing is None:
            by_pair[pair] = dict(row)
            continue
        if row.get("edge_scope") == "inter_course" and existing.get("edge_scope") != "inter_course":
            merged = dict(row)
            previous_rationale = existing.get("candidate_rationale")
        else:
            merged = dict(existing)
            previous_rationale = row.get("candidate_rationale")
        if previous_rationale and previous_rationale not in str(merged.get("candidate_rationale")):
            merged["candidate_rationale"] = (
                f"{merged.get('candidate_rationale')} Additional duplicate-scope rationale: {previous_rationale}"
            )
        by_pair[pair] = merged
    return sorted(by_pair.values(), key=_edge_pair)


def _has_alternative_path(source: str, target: str, adjacency: dict[str, set[str]]) -> bool:
    queue: deque[str] = deque(adjacency.get(source, set()))
    visited = {source}
    while queue:
        node = queue.popleft()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        queue.extend(adjacency.get(node, set()) - visited)
    return False


def _transitive_prune(
    clean_edges: list[dict[str, Any]], pruned_edges: list[dict[str, Any]], run_id: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    kept_by_pair = {_edge_pair(row): row for row in clean_edges}
    newly_pruned: list[dict[str, Any]] = []

    for pair, row in sorted(list(kept_by_pair.items())):
        adjacency: dict[str, set[str]] = defaultdict(set)
        for other_pair in kept_by_pair:
            if other_pair == pair:
                continue
            adjacency[other_pair[0]].add(other_pair[1])
        if _has_alternative_path(pair[0], pair[1], adjacency):
            kept_by_pair.pop(pair)
            pruned = {
                "source_kp_id": pair[0],
                "target_kp_id": pair[1],
                "prune_reason": "transitive_redundant",
                "prune_rationale": "Removed by deterministic transitive prune because another kept prerequisite path connects the same source and target.",
                "provenance": "llm_auto_pruned",
                "review_status": row.get("review_status"),
                "pruned_from_keep_confidence": row.get("keep_confidence"),
                "pruned_from_provenance": row.get("provenance"),
                "pruned_in_run": run_id,
            }
            pruned_edges.append(pruned)
            newly_pruned.append(pruned)

    summary = {
        "before_clean_count": len(clean_edges),
        "after_clean_count": len(kept_by_pair),
        "newly_pruned_count": len(newly_pruned),
        "newly_pruned": [
            {
                "source": row["source_kp_id"],
                "target": row["target_kp_id"],
                "reason": row["prune_reason"],
            }
            for row in newly_pruned
        ],
        "newly_unpruned": [],
    }
    return sorted(kept_by_pair.values(), key=_edge_pair), pruned_edges, summary


def build_append_bootstrap(
    *,
    p2_output_path: Path,
    base_p5_path: Path,
    output_path: Path,
    new_course_id: str,
    run_id: str,
) -> dict[str, Any]:
    p2_output = _load_json(p2_output_path)
    base_p5 = _load_json(base_p5_path)

    existing_pairs = {
        _edge_pair(row)
        for row in base_p5.get("clean_candidate_edges", []) + base_p5.get("pruned_edges", [])
        if isinstance(row, dict) and row.get("source_kp_id") and row.get("target_kp_id")
    }
    new_kps = _new_source_kps(p2_output, new_course_id)
    new_candidates = _dedupe_candidate_edges(
        [
            row
            for row in p2_output.get("candidate_prerequisite_edges", [])
            if isinstance(row, dict)
            and _edge_pair(row) not in existing_pairs
            and (row.get("source_kp_id") in new_kps or row.get("target_kp_id") in new_kps)
        ]
    )

    clean_edges = list(base_p5.get("clean_candidate_edges", []))
    pruned_edges = list(base_p5.get("pruned_edges", []))
    adjudication_trace = list(base_p5.get("adjudication_trace", []))

    appended_edges = [_candidate_to_clean_edge(row) for row in new_candidates]
    clean_edges.extend(appended_edges)
    for edge in appended_edges:
        adjudication_trace.append(
            {
                "source_kp_id": edge["source_kp_id"],
                "target_kp_id": edge["target_kp_id"],
                "generator_verdict": "keep",
                "generator_rationale": edge["keep_rationale"],
                "critic_verdict": "suggest_keep",
                "critic_rationale": "No LLM critic was run in deterministic append bootstrap; mark review_status optional for medium-confidence edges.",
                "resolver_verdict": "keep",
                "resolver_rationale": "Kept from P2 candidate edge for append-mode bootstrap pending future model scoring or LLM re-adjudication.",
                "consensus_type": "rule_based",
            }
        )

    clean_edges, pruned_edges, transitive_summary = _transitive_prune(
        clean_edges, pruned_edges, run_id
    )

    output = {
        "run_id": run_id,
        "stage_id": "p5",
        "clean_candidate_edges": clean_edges,
        "pruned_edges": pruned_edges,
        "adjudication_trace": adjudication_trace,
        "append_bootstrap_summary": {
            "base_p5_file": str(base_p5_path),
            "source_p2_file": str(p2_output_path),
            "new_course_id": new_course_id,
            "new_candidate_edges": len(new_candidates),
            "appended_edges_before_transitive": len(appended_edges),
        },
        "transitive_prune_summary": transitive_summary,
    }
    _dump_json(output_path, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--p2-output",
        type=Path,
        default=Path("data/final_artifacts/cs224n_cs231n_cs230_v1/p2_output_manual_append.json"),
    )
    parser.add_argument(
        "--base-p5",
        type=Path,
        default=Path("data/final_artifacts/cs224n_cs231n_v1/p5_output_transitive_pruned.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/final_artifacts/cs224n_cs231n_cs230_v1/p5_output_transitive_pruned.json"
        ),
    )
    parser.add_argument("--new-course-id", default="CS230")
    parser.add_argument("--run-id", default="p5_cs224n_cs231n_cs230_append_bootstrap")
    args = parser.parse_args()

    output = build_append_bootstrap(
        p2_output_path=args.p2_output,
        base_p5_path=args.base_p5,
        output_path=args.output,
        new_course_id=args.new_course_id,
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "clean_candidate_edges": len(output["clean_candidate_edges"]),
                "pruned_edges": len(output["pruned_edges"]),
                "append_bootstrap_summary": output["append_bootstrap_summary"],
                "transitive_prune_summary": output["transitive_prune_summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
