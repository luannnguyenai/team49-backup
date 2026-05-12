"""Review source datasets for guardrail-router fine-tuning extraction quality.

The goal is to decide whether each source supports deterministic, quality-aware
selection or only random sampling. EduVidQA is intentionally excluded because it
already has a dedicated preprocessing review in data/eduvidqa/reports.
"""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "guardrail_router" / "source_review"
VALIDATION_DIR = ROOT / "data" / "guardrail_router" / "source_validation"


BYPASS_PATTERNS = re.compile(
    r"(?i)("
    r"ignore (all )?(previous|prior|above) instructions|"
    r"disregard (all )?(previous|prior|above) instructions|"
    r"developer mode|dan mode|jailbreak|"
    r"you are now|act as|stay in character|"
    r"unfiltered|unrestricted|no restrictions|without restrictions|"
    r"do not refuse|don't refuse|never refuse|"
    r"bypass|override|"
    r"decode .* follow|base64|"
    r"bỏ qua|bo qua|không cần tuân|khong can tuan"
    r")"
)


@dataclass
class SourceReview:
    name: str
    total_rows: int
    quality_counts: dict[str, int]
    distributions: dict[str, dict[str, int]]
    selection_mode: str
    recommended_use: str
    cautions: list[str]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_value_counts(series: pd.Series, limit: int = 30) -> dict[str, int]:
    counts = series.fillna("<NA>").astype(str).value_counts().head(limit)
    return {str(key): int(value) for key, value in counts.items()}


def listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def download_hf(repo_id: str, filename: str) -> Path:
    return Path(
        hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=filename,
            local_dir=VALIDATION_DIR / "full_sources" / repo_id.replace("/", "__"),
        )
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def review_question_bank() -> SourceReview:
    path = (
        ROOT
        / "data"
        / "final_artifacts"
        / "cs224n_cs231n_cs230_v1"
        / "canonical"
        / "question_bank.jsonl"
    )
    rows = read_jsonl(path)
    df = pd.DataFrame(rows)
    gated = df[df["qa_gate_passed"] == True]  # noqa: E712 - pandas comparison.
    high_grounded = gated[
        gated["primary_kp_id"].notna()
        & gated["unit_id"].notna()
        & gated["course_id"].notna()
        & gated["lecture_id"].notna()
        & (gated["grounding_confidence"].fillna("") == "high")
    ]

    hard_possible = 0
    medium_possible = 0
    by_course_lecture: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_course: dict[str, set[str]] = defaultdict(set)
    for row in gated.to_dict(orient="records"):
        by_course_lecture[(row["course_id"], row["lecture_id"])].add(row["unit_id"])
        by_course[row["course_id"]].add(row["lecture_id"])
    for row in gated.to_dict(orient="records"):
        if len(by_course_lecture[(row["course_id"], row["lecture_id"])]) > 1:
            hard_possible += 1
        if len(by_course[row["course_id"]]) > 1:
            medium_possible += 1

    return SourceReview(
        name="question_bank_internal",
        total_rows=len(df),
        quality_counts={
            "qa_gate_passed": int(len(gated)),
            "high_grounded_with_kp_unit_course_lecture": int(len(high_grounded)),
            "can_make_hard_cross_pair_same_lecture_diff_unit": hard_possible,
            "can_make_medium_cross_pair_same_course_diff_lecture": medium_possible,
            "unique_primary_kp": int(gated["primary_kp_id"].nunique()),
            "unique_units": int(gated["unit_id"].nunique()),
        },
        distributions={
            "course_id": safe_value_counts(gated["course_id"]),
            "difficulty": safe_value_counts(gated["difficulty"]),
            "question_intent": safe_value_counts(gated["question_intent"]),
            "grounding_confidence": safe_value_counts(gated["grounding_confidence"]),
        },
        selection_mode="quality_filters_plus_stratified_sampling",
        recommended_use=(
            "Use all qa_gate_passed rows for ON_TOPIC, stratified by course/difficulty/intent. "
            "Use unit/lecture/course metadata to generate hard and medium cross-pair negatives deterministically."
        ),
        cautions=[
            "Do not split randomly by row; split by course/lecture/unit group before cross-pair generation.",
            "Question text is MCQ-style, so optionally transform into learner-style open questions later.",
        ],
    )


def review_clinc() -> SourceReview:
    path = VALIDATION_DIR / "github" / "clinc_oos_eval" / "data_full.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    split_counts = {key: len(value) for key, value in payload.items() if isinstance(value, list)}
    train_intents = Counter(label for _, label in payload.get("train", []))
    test_intents = Counter(label for _, label in payload.get("test", []))
    return SourceReview(
        name="clinc150_oos",
        total_rows=sum(split_counts.values()),
        quality_counts={
            **split_counts,
            "unique_train_intents": len(train_intents),
            "unique_test_intents": len(test_intents),
            "safe_off_topic_candidates": split_counts.get("train", 0)
            + split_counts.get("val", 0)
            + split_counts.get("test", 0)
            + split_counts.get("oos_train", 0)
            + split_counts.get("oos_val", 0)
            + split_counts.get("oos_test", 0),
        },
        distributions={
            "top_train_intents": dict(train_intents.most_common(20)),
            "top_test_intents": dict(test_intents.most_common(20)),
            "splits": split_counts,
        },
        selection_mode="stratified_by_intent_and_oos_split",
        recommended_use=(
            "Use deterministic stratified sampling across intents plus OOS rows for SAFE/OFF_TOPIC. "
            "Prefer diverse intents; cap translation/math-like intents if they overlap with education support."
        ),
        cautions=[
            "Some utterances are educational or translation-related, so filter if they overlap with current course scope.",
            "This source gives generic off-domain negatives, not lesson-near hard negatives.",
        ],
    )


def review_canttalk() -> SourceReview:
    train_path = download_hf(
        "nvidia/CantTalkAboutThis-Topic-Control-Dataset",
        "canttalkaboutthis_topic_control_mixtral.jsonl",
    )
    test_path = download_hf(
        "nvidia/CantTalkAboutThis-Topic-Control-Dataset",
        "canttalkaboutthis_topic_control_human_test_set.jsonl",
    )
    rows = read_jsonl(train_path) + read_jsonl(test_path)
    distractor_count = 0
    usable_distractors = 0
    domain_counts: Counter[str] = Counter()
    distractor_lengths: list[int] = []
    for row in rows:
        domain_counts[row.get("domain", "<NA>")] += 1
        for item in row.get("distractors", []) or []:
            text = item.get("distractor", "")
            distractor_count += 1
            words = len(text.split())
            distractor_lengths.append(words)
            if 3 <= words <= 40:
                usable_distractors += 1
    return SourceReview(
        name="canttalkaboutthis",
        total_rows=len(rows),
        quality_counts={
            "dialogues": len(rows),
            "distractors": distractor_count,
            "usable_distractors_len_3_40_words": usable_distractors,
            "domains": len(domain_counts),
            "min_distractor_words": min(distractor_lengths) if distractor_lengths else 0,
            "max_distractor_words": max(distractor_lengths) if distractor_lengths else 0,
        },
        distributions={"top_domains": dict(domain_counts.most_common(20))},
        selection_mode="field_based_extraction_from_distractors",
        recommended_use=(
            "Extract `distractors[*].distractor` as SAFE/OFF_TOPIC. Use domain/scenario/system_instruction "
            "as source metadata, then map to lesson scope externally."
        ),
        cautions=[
            "English only; does not cover multilingual jailbreak.",
            "Distractors are often easy off-topic, not hard lesson-near negatives.",
        ],
    )


def review_wildguard() -> SourceReview:
    train_path = download_hf("allenai/wildguardmix", "train/wildguard_train.parquet")
    test_path = download_hf("allenai/wildguardmix", "test/wildguard_test.parquet")
    df = pd.concat([pd.read_parquet(train_path), pd.read_parquet(test_path)], ignore_index=True)
    prompt = df["prompt"].fillna("").astype(str)
    harmful = df[df["prompt_harm_label"] == "harmful"]
    unharmful = df[df["prompt_harm_label"] == "unharmful"]
    bypass = df[prompt.str.contains(BYPASS_PATTERNS)]
    harmful_bypass = harmful[harmful["prompt"].fillna("").astype(str).str.contains(BYPASS_PATTERNS)]
    safe_prompt_only = unharmful[
        unharmful["prompt"].fillna("").astype(str).str.len().between(8, 1200)
    ]
    return SourceReview(
        name="wildguardmix",
        total_rows=len(df),
        quality_counts={
            "harmful_prompts": int(len(harmful)),
            "unharmful_prompts": int(len(unharmful)),
            "adversarial_true": int((df["adversarial"] == True).sum()),  # noqa: E712
            "bypass_pattern_any": int(len(bypass)),
            "harmful_with_bypass_pattern": int(len(harmful_bypass)),
            "safe_prompt_only_len_8_1200": int(len(safe_prompt_only)),
        },
        distributions={
            "prompt_harm_label": safe_value_counts(df["prompt_harm_label"]),
            "adversarial": safe_value_counts(df["adversarial"]),
            "subcategory": safe_value_counts(df["subcategory"]),
            "response_refusal_label": safe_value_counts(df["response_refusal_label"]),
        },
        selection_mode="label_and_pattern_filtered_sampling",
        recommended_use=(
            "Use prompt_harm_label for UNSAFE vs SAFE. Use bypass regex plus adversarial metadata to select "
            "JAILBREAK candidates; do not map every adversarial row to JAILBREAK."
        ),
        cautions=[
            "Contains prompt+response labels; router should use prompt only.",
            "Bypass regex is conservative and should be expanded/reviewed before final extraction.",
        ],
    )


def review_jailbreakv() -> SourceReview:
    main_path = download_hf("JailbreakV-28K/JailBreakV-28k", "JailBreakV_28K/JailBreakV_28K.csv")
    red_path = download_hf("JailbreakV-28K/JailBreakV-28k", "JailBreakV_28K/RedTeam_2K.csv")
    df = pd.concat([pd.read_csv(main_path), pd.read_csv(red_path)], ignore_index=True)
    text_subset = df[
        df["format"].fillna("").astype(str).str.lower().isin({"template", "logic", "persuade"})
        & (df["transfer_from_llm"] == True)  # noqa: E712
    ]
    no_image_dependency = text_subset[
        ~text_subset["format"]
        .fillna("")
        .astype(str)
        .str.lower()
        .isin({"figstep", "query-relevant"})
    ]
    return SourceReview(
        name="jailbreakv_28k",
        total_rows=len(df),
        quality_counts={
            "text_router_candidates_format_template_logic_persuade_transfer": int(len(text_subset)),
            "no_image_dependency_candidates": int(len(no_image_dependency)),
            "unique_policies": int(df["policy"].nunique()),
            "transfer_from_llm_true": int((df["transfer_from_llm"] == True).sum()),  # noqa: E712
        },
        distributions={
            "format": safe_value_counts(df["format"]),
            "policy": safe_value_counts(df["policy"]),
            "from": safe_value_counts(df["from"]),
            "transfer_from_llm": safe_value_counts(df["transfer_from_llm"]),
        },
        selection_mode="format_policy_and_transfer_filtered_sampling",
        recommended_use=(
            "Extract JAILBREAK from text-oriented formats and stratify by `format` and `policy`. "
            "Use redteam_query only as metadata or UNSAFE baseline, not as the jailbreak input."
        ),
        cautions=[
            "Many files are image/MLLM-related; filter out image-dependent methods for text router.",
            "Some samples contain offensive text; keep only prompt fields and mask downstream.",
        ],
    )


def review_multijail() -> SourceReview:
    languages = ["ar", "bn", "en", "it", "jv", "ko", "sw", "th", "vi", "zh"]
    frames = []
    for lang in languages:
        path = download_hf("walledai/MultiJail", f"data/{lang}-00000-of-00001.parquet")
        frame = pd.read_parquet(path)
        frame["language"] = lang
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    harm_counter: Counter[str] = Counter()
    for harms in df["harms"]:
        for harm in listish(harms):
            harm_counter[str(harm)] += 1
    vi = df[df["language"] == "vi"]
    return SourceReview(
        name="multijail",
        total_rows=len(df),
        quality_counts={
            "languages": len(languages),
            "vietnamese_rows": int(len(vi)),
            "english_rows": int((df["language"] == "en").sum()),
            "non_english_rows": int((df["language"] != "en").sum()),
            "unique_harm_categories": len(harm_counter),
        },
        distributions={
            "language": safe_value_counts(df["language"], limit=20),
            "top_harms": dict(harm_counter.most_common(30)),
            "source": safe_value_counts(df["source"]),
        },
        selection_mode="stratified_by_language_and_harm_category",
        recommended_use=(
            "Use as multilingual UNSAFE source and as eval slice. Mark JAILBREAK only when wrapped with "
            "bypass/prompt-injection augmentation; base rows are harmful requests, not necessarily jailbreaks."
        ),
        cautions=[
            "Language is split-derived, not a dataset column.",
            "Rows are unsafe prompts, not all jailbreaks by themselves.",
        ],
    )


def review_polyguard() -> SourceReview:
    path = download_hf("ToxicityPrompts/PolyGuardPrompts", "data/test-00000-of-00001.parquet")
    df = pd.read_parquet(path)
    harmful = df[df["prompt_harm_label"] == "harmful"]
    unharmful = df[df["prompt_harm_label"] == "unharmful"]
    adversarial_harmful = harmful[harmful["adversarial"] == True]  # noqa: E712
    return SourceReview(
        name="polyguardprompts",
        total_rows=len(df),
        quality_counts={
            "harmful_prompts": int(len(harmful)),
            "unharmful_prompts": int(len(unharmful)),
            "adversarial_harmful": int(len(adversarial_harmful)),
            "languages": int(df["language"].nunique()),
            "safe_prompt_only_len_8_1200": int(
                len(
                    unharmful[unharmful["prompt"].fillna("").astype(str).str.len().between(8, 1200)]
                )
            ),
        },
        distributions={
            "language": safe_value_counts(df["language"], limit=30),
            "prompt_harm_label": safe_value_counts(df["prompt_harm_label"]),
            "adversarial": safe_value_counts(df["adversarial"]),
            "subcategory": safe_value_counts(df["subcategory"]),
        },
        selection_mode="label_language_and_adversarial_filtered_sampling",
        recommended_use=(
            "Use as multilingual safety supplement. Stratify by language and prompt_harm_label; use adversarial "
            "as metadata/eval slice, not direct JAILBREAK label."
        ),
        cautions=[
            "It is primarily a benchmark-style test split, so avoid overusing if you want to preserve eval purity.",
            "Does not include Vietnamese in the current language distribution.",
        ],
    )


def review_beavertails() -> SourceReview:
    path = download_hf("PKU-Alignment/BeaverTails", "round0/30k/train.jsonl.gz")
    rows = read_jsonl(path)
    df = pd.DataFrame(rows)
    unsafe = df[df["is_safe"] == False]  # noqa: E712
    safe = df[df["is_safe"] == True]  # noqa: E712
    cat_counter: Counter[str] = Counter()
    for category in df["category"]:
        if isinstance(category, dict):
            for key, value in category.items():
                if value:
                    cat_counter[key] += 1
    return SourceReview(
        name="beavertails_optional",
        total_rows=len(df),
        quality_counts={
            "unsafe_prompts": int(len(unsafe)),
            "safe_prompts": int(len(safe)),
            "unsafe_prompt_only_len_8_1200": int(
                len(unsafe[unsafe["prompt"].fillna("").astype(str).str.len().between(8, 1200)])
            ),
            "safe_prompt_only_len_8_1200": int(
                len(safe[safe["prompt"].fillna("").astype(str).str.len().between(8, 1200)])
            ),
        },
        distributions={
            "is_safe": safe_value_counts(df["is_safe"]),
            "top_categories_true": dict(cat_counter.most_common(30)),
        },
        selection_mode="license_gated_label_and_category_filtered_sampling",
        recommended_use=(
            "Use only prompt + is_safe/category if license allows. Good optional unsafe fallback; do not train on response text."
        ),
        cautions=[
            "License is CC-BY-NC-4.0, so avoid for commercial production training unless acceptable.",
            "Safety QA data is less lesson-router-specific than WildGuard/PolyGuard.",
        ],
    )


def to_dict(review: SourceReview) -> dict[str, Any]:
    return {
        "name": review.name,
        "total_rows": review.total_rows,
        "quality_counts": review.quality_counts,
        "distributions": review.distributions,
        "selection_mode": review.selection_mode,
        "recommended_use": review.recommended_use,
        "cautions": review.cautions,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviews = [
        review_question_bank(),
        review_clinc(),
        review_canttalk(),
        review_wildguard(),
        review_jailbreakv(),
        review_multijail(),
        review_polyguard(),
        review_beavertails(),
    ]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "excluded": ["EduVidQA"],
        "reviews": [to_dict(review) for review in reviews],
    }
    write_json(OUT_DIR / "source_quality_review.json", payload)
    rows = []
    for review in reviews:
        rows.append(
            {
                "name": review.name,
                "total_rows": review.total_rows,
                "selection_mode": review.selection_mode,
                **review.quality_counts,
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "source_quality_summary.csv", index=False)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
