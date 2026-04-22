"""Render prerequisite KG edges to Graphviz DOT/SVG artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

from src.data_paths import (
    GPT54_EDGE_LABELS_FILE,
    KG_VISUALIZATIONS_DIR,
    MODERNBERT_LARGE_MASKED_V2_FILE,
    P5_INPUT_FILE,
    P5_TRANSITIVE_PRUNED_FILE,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _wrap_label(value: str, width: int = 24) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False)) or value


def _kp_name(kp_index: dict[str, dict[str, Any]], kp_id: str) -> str:
    row = kp_index.get(kp_id, {})
    return row.get("name") or row.get("canonical_name") or kp_id.removeprefix("kp_").replace("_", " ")


def _label_index(gpt54_labels: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not gpt54_labels:
        return {}
    return {
        (row["source_kp_id"], row["target_kp_id"]): row
        for row in gpt54_labels.get("edge_labels", [])
        if isinstance(row, dict) and row.get("source_kp_id") and row.get("target_kp_id")
    }


def _audit_verdict(audit_label: dict[str, Any] | None) -> str | None:
    if not audit_label:
        return None
    return audit_label.get("best_verdict") or audit_label.get("gpt54_verdict")


def _audit_rationale(audit_label: dict[str, Any] | None) -> str:
    if not audit_label:
        return ""
    return (
        audit_label.get("best_rationale")
        or audit_label.get("gpt54_rationale")
        or audit_label.get("baseline_gpt54_rationale")
        or ""
    )


def _edge_style(edge: dict[str, Any], audit_label: dict[str, Any] | None) -> tuple[str, str, str]:
    if _audit_verdict(audit_label) == "prune":
        return ("#d62728", "dashed", "GPT prune")
    if edge.get("keep_confidence") == "high":
        return ("#1b7837", "solid", "high")
    if edge.get("keep_confidence") == "low":
        return ("#f59e0b", "dotted", "low")
    return ("#4b5563", "solid", "medium")


def _ml_edge_style(edge: dict[str, Any], score: dict[str, Any] | None) -> tuple[str, str, str, float]:
    if not score:
        return ("#9ca3af", "dotted", "no score", 1.0)

    strength = float(score.get("edge_strength", 0.0))
    margin = float(score.get("direction_margin", 0.0))
    bidirectional = float(score.get("bidirectional_score", 0.0))

    if margin < -0.02:
        color = "#dc2626"
    elif margin > 0.02:
        color = "#16a34a"
    else:
        color = "#f59e0b"

    penwidth = 1.0 + max(0.0, min(1.0, strength)) * 3.0
    label = f"s={strength:.2f}\\nm={margin:+.2f}\\nr={bidirectional:.2f}"
    return (color, "solid", label, penwidth)


def _render_dot(
    *,
    edges: list[dict[str, Any]],
    kp_index: dict[str, dict[str, Any]],
    labels: dict[tuple[str, str], dict[str, Any]],
    title: str,
) -> str:
    node_ids = sorted({edge["source_kp_id"] for edge in edges} | {edge["target_kp_id"] for edge in edges})
    indegree = Counter(edge["target_kp_id"] for edge in edges)
    outdegree = Counter(edge["source_kp_id"] for edge in edges)

    lines = [
        "digraph KG {",
        "  graph [",
        '    rankdir=LR,',
        '    bgcolor="white",',
        '    pad="0.35",',
        '    nodesep="0.35",',
        '    ranksep="0.9",',
        f'    label="{_dot_escape(title)}",',
        '    labelloc="t",',
        '    fontsize="22",',
        '    fontname="Helvetica"',
        "  ];",
        '  node [shape=box, style="rounded,filled", fillcolor="#f8fafc", color="#94a3b8", penwidth=1.2, fontname="Helvetica", fontsize=10, margin="0.08,0.05"];',
        '  edge [fontname="Helvetica", fontsize=8, arrowsize=0.7, penwidth=1.4];',
    ]

    for kp_id in node_ids:
        name = _wrap_label(_kp_name(kp_index, kp_id))
        fill = "#ecfeff" if outdegree[kp_id] > indegree[kp_id] else "#f8fafc"
        if indegree[kp_id] > outdegree[kp_id]:
            fill = "#fff7ed"
        tooltip = kp_index.get(kp_id, {}).get("description", "")
        lines.append(
            f'  "{_dot_escape(kp_id)}" [label="{_dot_escape(name)}", fillcolor="{fill}", tooltip="{_dot_escape(tooltip)}"];'
        )

    for edge in edges:
        source = edge["source_kp_id"]
        target = edge["target_kp_id"]
        audit_label = labels.get((source, target))
        color, style, short_label = _edge_style(edge, audit_label)
        if _audit_verdict(audit_label) == "prune":
            tooltip = _audit_rationale(audit_label)
        else:
            tooltip = edge.get("keep_rationale", "")
        lines.append(
            f'  "{_dot_escape(source)}" -> "{_dot_escape(target)}" '
            f'[color="{color}", fontcolor="{color}", style="{style}", label="{_dot_escape(short_label)}", tooltip="{_dot_escape(tooltip)}"];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def _render_ml_dot(
    *,
    edges: list[dict[str, Any]],
    kp_index: dict[str, dict[str, Any]],
    score_index: dict[tuple[str, str], dict[str, Any]],
    title: str,
) -> str:
    node_ids = sorted({edge["source_kp_id"] for edge in edges} | {edge["target_kp_id"] for edge in edges})
    indegree = Counter(edge["target_kp_id"] for edge in edges)
    outdegree = Counter(edge["source_kp_id"] for edge in edges)

    lines = [
        "digraph KG {",
        "  graph [",
        '    rankdir=LR,',
        '    bgcolor="white",',
        '    pad="0.35",',
        '    nodesep="0.35",',
        '    ranksep="0.9",',
        f'    label="{_dot_escape(title)}",',
        '    labelloc="t",',
        '    fontsize="22",',
        '    fontname="Helvetica"',
        "  ];",
        '  node [shape=box, style="rounded,filled", fillcolor="#f8fafc", color="#94a3b8", penwidth=1.2, fontname="Helvetica", fontsize=10, margin="0.08,0.05"];',
        '  edge [fontname="Helvetica", fontsize=8, arrowsize=0.7];',
    ]

    for kp_id in node_ids:
        name = _wrap_label(_kp_name(kp_index, kp_id))
        fill = "#ecfeff" if outdegree[kp_id] > indegree[kp_id] else "#f8fafc"
        if indegree[kp_id] > outdegree[kp_id]:
            fill = "#fff7ed"
        tooltip = kp_index.get(kp_id, {}).get("description", "")
        lines.append(
            f'  "{_dot_escape(kp_id)}" [label="{_dot_escape(name)}", fillcolor="{fill}", tooltip="{_dot_escape(tooltip)}"];'
        )

    for edge in edges:
        source = edge["source_kp_id"]
        target = edge["target_kp_id"]
        score = score_index.get((source, target))
        color, style, short_label, penwidth = _ml_edge_style(edge, score)
        tooltip = json.dumps(score, ensure_ascii=False) if score else "No ML score"
        lines.append(
            f'  "{_dot_escape(source)}" -> "{_dot_escape(target)}" '
            f'[color="{color}", fontcolor="{color}", style="{style}", penwidth="{penwidth:.2f}", label="{_dot_escape(short_label)}", tooltip="{_dot_escape(tooltip)}"];'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def _score_index(score_payload: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    if not score_payload:
        return {}
    return {
        (row["source_kp_id"], row["target_kp_id"]): row
        for row in score_payload.get("scored_edges", [])
        if isinstance(row, dict) and row.get("source_kp_id") and row.get("target_kp_id")
    }


def _run_dot(dot_path: Path, svg_path: Path) -> None:
    subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)


def build_visualizations(
    *,
    p5_path: Path,
    p5_input_path: Path,
    gpt54_labels_path: Path | None,
    modernbert_large_scores_path: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    p5 = _load_json(p5_path)
    p5_input = _load_json(p5_input_path)
    gpt54_labels = _load_json(gpt54_labels_path) if gpt54_labels_path and gpt54_labels_path.exists() else None
    modernbert_large_scores = (
        _load_json(modernbert_large_scores_path)
        if modernbert_large_scores_path and modernbert_large_scores_path.exists()
        else None
    )

    kp_index = {
        row["global_kp_id"]: row
        for row in p5_input.get("global_kps", [])
        if isinstance(row, dict) and row.get("global_kp_id")
    }
    labels = _label_index(gpt54_labels)
    large_score_index = _score_index(modernbert_large_scores)

    clean_edges = p5.get("clean_candidate_edges", [])
    audit_edges = clean_edges
    kept_only_edges = [
        edge
        for edge in clean_edges
        if _audit_verdict(labels.get((edge["source_kp_id"], edge["target_kp_id"]))) != "prune"
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    for name, edges, title in [
        (
            "kg_p5_audit",
            audit_edges,
            "P5 prerequisite KG audit view: green=high, gray=medium, orange=low, red dashed=GPT-5.4 prune suggestion",
        ),
        ("kg_p5_kept_only", kept_only_edges, "P5 prerequisite KG kept-only view after GPT-5.4 audit suggestions"),
    ]:
        dot_path = output_dir / f"{name}.dot"
        svg_path = output_dir / f"{name}.svg"
        dot_path.write_text(
            _render_dot(edges=edges, kp_index=kp_index, labels=labels, title=title),
            encoding="utf-8",
        )
        _run_dot(dot_path, svg_path)
        artifacts[f"{name}_dot"] = str(dot_path)
        artifacts[f"{name}_svg"] = str(svg_path)

    if large_score_index:
        name = "kg_modernbert_large"
        dot_path = output_dir / f"{name}.dot"
        svg_path = output_dir / f"{name}.svg"
        dot_path.write_text(
            _render_ml_dot(
                edges=clean_edges,
                kp_index=kp_index,
                score_index=large_score_index,
                title="ModernBERT-large masked-label score view: green=forward margin > .02, red=reverse margin > .02, orange=ambiguous",
            ),
            encoding="utf-8",
        )
        _run_dot(dot_path, svg_path)
        artifacts[f"{name}_dot"] = str(dot_path)
        artifacts[f"{name}_svg"] = str(svg_path)

    summary = {
        "source_p5_file": str(p5_path),
        "source_p5_input_file": str(p5_input_path),
        "source_gpt54_labels_file": str(gpt54_labels_path) if gpt54_labels_path else None,
        "source_modernbert_large_scores_file": str(modernbert_large_scores_path) if modernbert_large_scores_path else None,
        "audit_edges": len(audit_edges),
        "kept_only_edges": len(kept_only_edges),
        "gpt54_prune_suggestions": len(audit_edges) - len(kept_only_edges),
        "audit_nodes": len({edge["source_kp_id"] for edge in audit_edges} | {edge["target_kp_id"] for edge in audit_edges}),
        "kept_only_nodes": len(
            {edge["source_kp_id"] for edge in kept_only_edges} | {edge["target_kp_id"] for edge in kept_only_edges}
        ),
        "artifacts": artifacts,
    }
    _dump_json(output_dir / "kg_visualization_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p5", type=Path, default=P5_TRANSITIVE_PRUNED_FILE)
    parser.add_argument("--p5-input", type=Path, default=P5_INPUT_FILE)
    parser.add_argument("--gpt54-labels", type=Path, default=GPT54_EDGE_LABELS_FILE)
    parser.add_argument(
        "--modernbert-large-scores",
        type=Path,
        default=MODERNBERT_LARGE_MASKED_V2_FILE,
    )
    parser.add_argument("--output-dir", type=Path, default=KG_VISUALIZATIONS_DIR)
    args = parser.parse_args()

    summary = build_visualizations(
        p5_path=args.p5,
        p5_input_path=args.p5_input,
        gpt54_labels_path=args.gpt54_labels,
        modernbert_large_scores_path=args.modernbert_large_scores,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
