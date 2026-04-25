"""Normalize generated P3c question artifacts into P4 review artifacts.

This is a deterministic bridge for manually reviewed P3c outputs. It does not
invent new questions; it only reshapes accepted P3c question banks into the P4
contract consumed by the canonical exporter.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


PHASE_MULTIPLIERS = {
    "placement": 1.0,
    "mini_quiz": 0.8,
    "skip_verification": 1.0,
    "bridge_check": 1.0,
    "final_quiz": 1.2,
    "transfer": 1.1,
    "review": 0.7,
}

ALLOWED_PHASES = tuple(PHASE_MULTIPLIERS)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slugify(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")


def _lecture_dir_name(lecture_id: str | None) -> str:
    match = re.search(r"(\d+)", lecture_id or "")
    if not match:
        return "L0"
    return f"L{int(match.group(1))}"


def _iter_json_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _load_p3a_index(p3a_root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in _iter_json_files(p3a_root):
        artifact = _load_json(path)
        for row in artifact.get("learning_salience", []):
            if isinstance(row, dict) and row.get("unit_id"):
                index[row["unit_id"]] = row
    return index


def _load_p3b_index(p3b_root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in _iter_json_files(p3b_root):
        artifact = _load_json(path)
        for row in artifact.get("clips", []):
            if isinstance(row, dict) and row.get("unit_id"):
                index[row["unit_id"]] = row
    return index


def _option_id(option: Any, index: int) -> str:
    if isinstance(option, dict):
        value = option.get("option_id") or option.get("id") or option.get("label")
        if value:
            return str(value)
    return chr(ord("A") + index)


def _option_text(option: Any) -> str:
    if isinstance(option, dict):
        return str(option.get("text") or option.get("value") or "").strip()
    return str(option).strip()


def _extract_choices(question: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_choices = question.get("choices") or question.get("options") or []
    choices: list[str] = []
    ids: list[str] = []
    for index, option in enumerate(raw_choices):
        text = _option_text(option)
        if not text:
            continue
        choices.append(text)
        ids.append(_option_id(option, index))
    return choices, ids


def _answer_index(question: dict[str, Any], choices: list[str], option_ids: list[str]) -> int | None:
    raw_index = question.get("answer_index")
    if isinstance(raw_index, int) and 0 <= raw_index < len(choices):
        return raw_index

    raw_key = (
        question.get("correct_option_id")
        or question.get("answer_key")
        or question.get("correct_option")
        or question.get("correct_choice")
    )
    if raw_key is not None:
        key = str(raw_key).strip()
        for index, option_id in enumerate(option_ids):
            if option_id.casefold() == key.casefold():
                return index
        if len(key) == 1 and key.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            index = ord(key.upper()) - ord("A")
            if 0 <= index < len(choices):
                return index

    raw_answer = question.get("correct_answer")
    if isinstance(raw_answer, str) and raw_answer.strip():
        answer = raw_answer.strip()
        for index, choice in enumerate(choices):
            if choice.strip() == answer:
                return index

    return None


def _difficulty_label(prior: Any) -> str:
    try:
        value = float(prior)
    except (TypeError, ValueError):
        return "medium"
    if value < 0.4:
        return "easy"
    if value < 0.7:
        return "medium"
    return "hard"


def _discrimination_prior(intent: str | None) -> float:
    if intent in {"diagnostic", "application"}:
        return 1.05
    if intent == "procedural":
        return 0.95
    return 0.85


def _normalize_video_clip_ref(source_ref: dict[str, Any], p3b_clip: dict[str, Any] | None) -> dict[str, Any] | None:
    raw_ref = source_ref.get("video_clip_ref")
    if isinstance(raw_ref, dict):
        return raw_ref
    if p3b_clip and isinstance(p3b_clip.get("video_clip_ref"), dict):
        video_clip_ref = dict(p3b_clip["video_clip_ref"])
        video_clip_ref.setdefault("clip_url", p3b_clip.get("clip_path"))
        video_clip_ref.setdefault("local_path", p3b_clip.get("clip_path"))
        return video_clip_ref
    return None


def _normalize_source_ref(
    *,
    question: dict[str, Any],
    course_id: str,
    lecture_id: str,
    unit_id: str,
    p3b_clip: dict[str, Any] | None,
) -> dict[str, Any]:
    source_ref = dict(question.get("source_ref") or {})
    source_ref.setdefault("course_id", course_id)
    source_ref.setdefault("lecture_id", lecture_id)
    source_ref.setdefault("unit_id", unit_id)
    source_ref.setdefault("multimodal_signals_used", [])

    signals = set(str(signal) for signal in source_ref.get("multimodal_signals_used", []) if str(signal).strip())
    if source_ref.get("evidence_span"):
        signals.add("transcript")
    video_clip_ref = _normalize_video_clip_ref(source_ref, p3b_clip)
    if video_clip_ref:
        source_ref["video_clip_ref"] = video_clip_ref
        signals.add("video_frame")
    source_ref["multimodal_signals_used"] = sorted(signals)
    return source_ref


def _source_ref_to_evidence(source_ref: dict[str, Any]) -> dict[str, Any]:
    evidence_span = source_ref.get("evidence_span")
    timestamps: list[str] = []
    if source_ref.get("transcript_ts"):
        timestamps.append(str(source_ref["transcript_ts"]))
    elif isinstance(source_ref.get("timestamp_start"), (int, float)):
        timestamps.append(str(source_ref["timestamp_start"]))
    return {
        "source": "transcript",
        "transcript_quotes": [evidence_span] if evidence_span else [],
        "timestamps": timestamps,
    }


def _normalize_question(
    *,
    question: dict[str, Any],
    course_id: str,
    lecture_id: str,
    unit_id: str,
    p3b_clip: dict[str, Any] | None,
) -> dict[str, Any]:
    choices, option_ids = _extract_choices(question)
    answer_index = _answer_index(question, choices, option_ids)
    if answer_index is None:
        raise ValueError(f"Cannot determine answer_index for {question.get('item_id')}")

    source_ref = _normalize_source_ref(
        question=question,
        course_id=course_id,
        lecture_id=lecture_id,
        unit_id=unit_id,
        p3b_clip=p3b_clip,
    )
    intent = question.get("question_intent") or "conceptual"
    difficulty_prior = question.get("difficulty_prior")

    return {
        "item_id": question["item_id"],
        "item_type": "concept_mcq",
        "knowledge_scope": question.get("knowledge_scope") or "lecture_reinforcement",
        "render_mode": question.get("render_mode") or "standard_mcq",
        "type": question.get("type") or "multiple_choice",
        "question": question.get("question") or question.get("stem"),
        "stem_format": question.get("stem_format") or "plain_text",
        "choices_format": question.get("choices_format") or "plain_text",
        "choices": choices,
        "answer_index": answer_index,
        "explanation": question.get("explanation") or question.get("rationale"),
        "answer_explanation_format": question.get("answer_explanation_format") or "plain_text",
        "primary_kp_id": question.get("primary_kp_id"),
        "difficulty": question.get("difficulty") or _difficulty_label(difficulty_prior),
        "code_question_style": question.get("code_question_style"),
        "requires_monospace": bool(question.get("requires_monospace", False)),
        "code_block": question.get("code_block"),
        "evidence": _source_ref_to_evidence(source_ref),
        "source_ref": source_ref,
        "qa_gate_passed": bool(question.get("qa_gate_passed", True)),
        "review_status": question.get("review_status") or "not_required",
        "repair_history": question.get("repair_history") or [],
        "provenance": question.get("provenance") or "vlm_grounded",
        "difficulty_prior": difficulty_prior,
        "question_intent": intent,
        "secondary_kp_ids": question.get("secondary_kp_ids") or question.get("related_kp_ids") or [],
    }


def _normalize_role(raw_role: Any, *, is_primary: bool = False) -> str:
    role = str(raw_role or "").strip().casefold()
    if role in {"primary", "main"} or is_primary:
        return "primary"
    if role in {"secondary", "supporting", "support"}:
        return "secondary" if role != "support" else "support"
    return "secondary"


def _normalize_item_kp_map(raw_maps: list[dict[str, Any]], questions: list[dict[str, Any]]) -> list[dict[str, str]]:
    question_by_id = {question["item_id"]: question for question in questions}
    rows: dict[tuple[str, str, str], dict[str, str]] = {}

    def add(item_id: str, kp_id: str | None, role: str) -> None:
        if not item_id or not kp_id:
            return
        normalized_role = _normalize_role(role, is_primary=False)
        rows[(item_id, kp_id, normalized_role)] = {
            "item_id": item_id,
            "global_kp_id": kp_id,
            "role": normalized_role,
        }

    for raw in raw_maps:
        item_id = raw.get("item_id")
        if not item_id:
            continue
        if raw.get("primary_kp_id") or raw.get("secondary_kp_ids"):
            add(item_id, raw.get("primary_kp_id"), "primary")
            for kp_id in raw.get("secondary_kp_ids") or []:
                add(item_id, kp_id, "secondary")
            continue
        kp_id = raw.get("global_kp_id")
        question = question_by_id.get(item_id, {})
        role = raw.get("role") or raw.get("map_role") or raw.get("planner_role")
        add(item_id, kp_id, _normalize_role(role, is_primary=kp_id == question.get("primary_kp_id")))

    for question in questions:
        item_id = question["item_id"]
        add(item_id, question.get("primary_kp_id"), "primary")
        for kp_id in question.get("secondary_kp_ids") or []:
            add(item_id, kp_id, "secondary")

    return sorted(rows.values(), key=lambda row: (row["item_id"], row["role"], row["global_kp_id"]))


def _qa_output(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": question["item_id"],
        "qa_gate_passed": question["qa_gate_passed"],
        "alignment_verdict": "pass",
        "distractor_verdict": "pass",
        "rubric_verdict": "n_a",
        "evidence_verdict": "pass",
        "qa_rationale": "Accepted after deterministic P3c validation and P4 normalization.",
        "recommended_action": "accept",
        "repairable": False,
        "revise_hints": [],
    }


def _calibration_row(question: dict[str, Any]) -> dict[str, Any]:
    choices = question.get("choices") or []
    guessing_prior = round(1 / len(choices), 3) if choices else 0.25
    intent = question.get("question_intent")
    return {
        "item_id": question["item_id"],
        "is_calibrated": False,
        "calibration_method": "prior_only",
        "difficulty_prior": question.get("difficulty_prior"),
        "discrimination_prior": _discrimination_prior(intent),
        "guessing_prior": guessing_prior,
        "calibration_confidence": "medium",
        "calibration_rationale": "Prior-only bootstrap from P3c difficulty and question intent; no learner response data yet.",
    }


def _phase_suitability(question: dict[str, Any]) -> dict[str, str]:
    intent = question.get("question_intent")
    difficulty = question.get("difficulty")
    suitability = {phase: "medium" for phase in ALLOWED_PHASES}
    suitability["mini_quiz"] = "high"
    suitability["review"] = "high"

    if difficulty == "easy":
        suitability["placement"] = "high"
        suitability["final_quiz"] = "low"
    elif difficulty == "hard":
        suitability["skip_verification"] = "high"
        suitability["final_quiz"] = "high"

    if intent in {"diagnostic", "procedural"}:
        suitability["bridge_check"] = "high"
        suitability["skip_verification"] = "high"
    if intent == "application":
        suitability["transfer"] = "high"
        suitability["final_quiz"] = "high"
    if intent == "conceptual" and difficulty != "hard":
        suitability["placement"] = "high"

    return suitability


def _phase_row(question: dict[str, Any]) -> dict[str, Any]:
    suitability = _phase_suitability(question)
    primary_phase = "mini_quiz"
    if suitability.get("placement") == "high":
        primary_phase = "placement"
    elif suitability.get("skip_verification") == "high":
        primary_phase = "skip_verification"
    return {
        "item_id": question["item_id"],
        "primary_phase": primary_phase,
        "secondary_phases": [phase for phase in ALLOWED_PHASES if phase != primary_phase and suitability[phase] != "low"],
        "suitability_by_phase": suitability,
        "phase_multiplier_by_phase": PHASE_MULTIPLIERS,
        "phase_rationale": "Deterministic phase mapping from P3c question intent and difficulty prior.",
    }


def normalize_course_p3c_to_p4(
    *,
    course_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    p3a_index = _load_p3a_index(course_dir / "processed" / "P3a")
    p3b_index = _load_p3b_index(course_dir / "processed" / "P3b")
    p3c_root = course_dir / "processed" / "P3c"
    p4_root = course_dir / "processed" / "P4"

    if p4_root.exists() and overwrite:
        shutil.rmtree(p4_root)

    summary = {
        "course_id": course_dir.name,
        "input_files": 0,
        "output_files": 0,
        "questions": 0,
        "item_kp_map": 0,
        "missing_p3a_units": [],
        "missing_p3b_units": [],
    }

    for path in _iter_json_files(p3c_root):
        artifact = _load_json(path)
        unit_id = artifact.get("unit_id")
        lecture_id = artifact.get("lecture_id")
        questions_raw = artifact.get("question_bank") or []
        if not unit_id or not lecture_id:
            continue

        salience = p3a_index.get(unit_id)
        p3b_clip = p3b_index.get(unit_id)
        if salience is None:
            summary["missing_p3a_units"].append(unit_id)
        if p3b_clip is None:
            summary["missing_p3b_units"].append(unit_id)

        questions = [
            _normalize_question(
                question=question,
                course_id=artifact.get("course_id") or course_dir.name,
                lecture_id=lecture_id,
                unit_id=unit_id,
                p3b_clip=p3b_clip,
            )
            for question in questions_raw
        ]
        item_kp_map = _normalize_item_kp_map(artifact.get("item_kp_map") or [], questions) if questions else []

        output = {
            "run_id": f"p4_deterministic_{course_dir.name.lower()}",
            "stage_id": "P4_review_repair_calibration_phase_map",
            "course_id": artifact.get("course_id") or course_dir.name,
            "lecture_id": lecture_id,
            "unit_id": unit_id,
            "youtube_url": None,
            "assessment_purpose": "segment_checkpoint",
            "grounding_mode": "transcript_and_video_clip",
            "grounding_confidence": "high" if questions else "not_applicable",
            "needs_video_clip": bool(questions),
            "question_intent": (salience or {}).get("question_intent") or (questions[0].get("question_intent") if questions else None),
            "target_item_count": len(questions),
            "review_summary": {
                "source_p3c_file": str(path),
                "review_mode": "deterministic_normalization_after_p3c_validation",
                "accepted_items": len(questions),
                "repaired_items": 0,
                "rejected_items": 0,
            },
            "qa_outputs": [_qa_output(question) for question in questions],
            "repaired_question_bank": questions,
            "item_kp_map": item_kp_map,
            "repair_actions": [],
            "item_calibration_bootstrap": [_calibration_row(question) for question in questions],
            "item_phase_map": [_phase_row(question) for question in questions],
        }

        lecture_dir = p4_root / _lecture_dir_name(lecture_id)
        output_name = f"{_slugify(unit_id)}-p4.json"
        _dump_json(lecture_dir / output_name, output)
        summary["input_files"] += 1
        summary["output_files"] += 1
        summary["questions"] += len(questions)
        summary["item_kp_map"] += len(item_kp_map)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course-dir", type=Path, default=Path("data/courses/CS230"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = normalize_course_p3c_to_p4(course_dir=args.course_dir, overwrite=args.overwrite)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["missing_p3a_units"] or summary["missing_p3b_units"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
