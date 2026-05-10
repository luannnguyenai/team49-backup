"""Deep source review for guardrail-router dataset extraction.

Excluded by request:
- EduVidQA
- PolyGuardPrompts
- BeaverTails

Reviewed:
- CantTalkAboutThis
- CLINC150/OOS
- WildGuardMix
- JailBreakV-28K
- MultiJail
"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from huggingface_hub import hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = ROOT / "data" / "guardrail_router" / "source_validation"
OUT_DIR = ROOT / "data" / "guardrail_router" / "deep_source_review"


BYPASS_PATTERNS = re.compile(
    r"(?i)(?:"
    r"ignore (?:all )?(?:previous|prior|above) instructions|"
    r"disregard (?:all )?(?:previous|prior|above) instructions|"
    r"developer mode|dan mode|jailbreak|"
    r"you are now|act as|stay in character|"
    r"unfiltered|unrestricted|no restrictions|without restrictions|"
    r"do not refuse|don't refuse|never refuse|"
    r"bypass|override|"
    r"decode .* follow|base64|"
    r"bỏ qua|bo qua|không cần tuân|khong can tuan"
    r")"
)

LESSON_OVERLAP_CLINC_INTENTS = {
    "definition",
    "translate",
    "spelling",
    "calculator",
    "measurement_conversion",
    "what_is_your_name",
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def words(text: Any) -> int:
    return len(str(text or "").split())


def chars(text: Any) -> int:
    return len(str(text or "").strip())


def quantiles(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"min": None, "p05": None, "p50": None, "p95": None, "max": None, "mean": None}
    series = pd.Series(values)
    return {
        "min": int(series.min()),
        "p05": float(series.quantile(0.05)),
        "p50": float(series.quantile(0.5)),
        "p95": float(series.quantile(0.95)),
        "max": int(series.max()),
        "mean": float(series.mean()),
    }


def value_counts(series: pd.Series, limit: int = 50) -> dict[str, int]:
    counts = series.fillna("<NA>").astype(str).value_counts().head(limit)
    return {key: int(value) for key, value in counts.items()}


def bool_sum(series: pd.Series) -> int:
    return int(series.fillna(False).astype(bool).sum())


def prompt_common_stats(df: pd.DataFrame, column: str = "prompt") -> dict[str, Any]:
    text = df[column].fillna("").astype(str)
    word_counts = [words(item) for item in text]
    stripped = text.str.strip()
    return {
        "rows": int(len(df)),
        "nonempty": int((stripped != "").sum()),
        "unique": int(stripped.nunique()),
        "duplicates": int(len(df) - stripped.nunique()),
        "word_count": quantiles(word_counts),
        "usable_len_3_220_words": int(pd.Series(word_counts).between(3, 220).sum()),
        "usable_len_5_120_words": int(pd.Series(word_counts).between(5, 120).sum()),
    }


def review_canttalk() -> dict[str, Any]:
    train_path = download_hf(
        "nvidia/CantTalkAboutThis-Topic-Control-Dataset",
        "canttalkaboutthis_topic_control_mixtral.jsonl",
    )
    test_path = download_hf(
        "nvidia/CantTalkAboutThis-Topic-Control-Dataset",
        "canttalkaboutthis_topic_control_human_test_set.jsonl",
    )
    dialogues = read_jsonl(train_path) + read_jsonl(test_path)
    records = []
    for row in dialogues:
        for item in row.get("distractors", []) or []:
            records.append(
                {
                    "domain": row.get("domain"),
                    "scenario": row.get("scenario"),
                    "system_instruction": row.get("system_instruction"),
                    "bot_turn": item.get("bot turn"),
                    "prompt": item.get("distractor"),
                }
            )
    df = pd.DataFrame(records)
    word_counts = df["prompt"].map(words)
    clean = df[
        df["prompt"].fillna("").astype(str).str.strip().ne("")
        & word_counts.between(3, 40)
        & ~df["prompt"].fillna("").astype(str).str.contains(BYPASS_PATTERNS)
    ]
    per_domain_target = clean.groupby("domain").head(100)
    return {
        "source": "CantTalkAboutThis",
        "role": "SAFE_OFF_TOPIC_topic_control",
        "common": prompt_common_stats(df),
        "quality_filters": {
            "nonempty_len_3_40_no_bypass": int(len(clean)),
            "balanced_cap_100_per_domain": int(len(per_domain_target)),
            "domains": int(df["domain"].nunique()),
        },
        "distributions": {
            "domain": value_counts(df["domain"]),
        },
        "recommended_quota_v1": 800,
        "selection": [
            "Extract only `distractors[*].distractor`.",
            "Stratify by domain, cap around 90-100 per domain.",
            "Use as easy off-topic; do not use as hard lesson-scope negatives.",
        ],
        "quality_verdict": "high_quality_field_extraction",
    }


def review_clinc() -> dict[str, Any]:
    path = VALIDATION_DIR / "github" / "clinc_oos_eval" / "data_full.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for split, rows in payload.items():
        for text, intent in rows:
            records.append({"split": split, "prompt": text, "intent": intent})
    df = pd.DataFrame(records)
    non_overlap = df[~df["intent"].isin(LESSON_OVERLAP_CLINC_INTENTS)]
    diversified = non_overlap.groupby("intent").head(8)
    oos = df[df["intent"] == "oos"]
    in_scope_safe = non_overlap[non_overlap["intent"] != "oos"]
    return {
        "source": "CLINC150/OOS",
        "role": "SAFE_OFF_TOPIC_generic_out_of_domain",
        "common": prompt_common_stats(df),
        "quality_filters": {
            "non_overlap_with_lesson_like_intents": int(len(non_overlap)),
            "explicit_oos": int(len(oos)),
            "non_overlap_in_scope_intents": int(in_scope_safe["intent"].nunique()),
            "balanced_cap_8_per_intent_after_overlap_filter": int(len(diversified)),
        },
        "distributions": {
            "split": value_counts(df["split"]),
            "intent_top": value_counts(df["intent"], limit=30),
            "excluded_lesson_overlap_intents": {
                key: int((df["intent"] == key).sum()) for key in sorted(LESSON_OVERLAP_CLINC_INTENTS)
            },
        },
        "recommended_quota_v1": 700,
        "selection": [
            "Exclude or downweight lesson-overlap intents such as definition, translate, spelling, calculator.",
            "Use explicit OOS plus a capped number per remaining intent.",
            "Keep as easy/generic off-topic only.",
        ],
        "quality_verdict": "high_quality_stratified_generic_off_topic",
    }


def review_wildguard() -> dict[str, Any]:
    train_path = download_hf("allenai/wildguardmix", "train/wildguard_train.parquet")
    test_path = download_hf("allenai/wildguardmix", "test/wildguard_test.parquet")
    df = pd.concat([pd.read_parquet(train_path), pd.read_parquet(test_path)], ignore_index=True)
    prompt = df["prompt"].fillna("").astype(str)
    labeled = df[df["prompt_harm_label"].isin(["harmful", "unharmful"])].copy()
    agreement_available = labeled[labeled["prompt_harm_agreement"].notna()].copy()
    high_agreement = agreement_available[agreement_available["prompt_harm_agreement"].fillna(0) >= 2]
    harmful = labeled[labeled["prompt_harm_label"] == "harmful"]
    safe = labeled[labeled["prompt_harm_label"] == "unharmful"]
    harmful_clean = harmful[harmful["prompt"].fillna("").astype(str).map(words).between(5, 220)]
    safe_clean = safe[safe["prompt"].fillna("").astype(str).map(words).between(5, 180)]
    high_agreement_harmful_clean = high_agreement[
        (high_agreement["prompt_harm_label"] == "harmful")
        & high_agreement["prompt"].fillna("").astype(str).map(words).between(5, 220)
    ]
    harmful_bypass = harmful_clean[harmful_clean["prompt"].fillna("").astype(str).str.contains(BYPASS_PATTERNS)]
    harmful_non_bypass = harmful_clean[
        ~harmful_clean["prompt"].fillna("").astype(str).str.contains(BYPASS_PATTERNS)
    ]
    category_balanced_unsafe = harmful_non_bypass.groupby("subcategory").head(120)
    category_balanced_jailbreak = harmful_bypass.groupby("subcategory").head(80)
    return {
        "source": "WildGuardMix",
        "role": "UNSAFE_and_JAILBREAK_candidate",
        "common": prompt_common_stats(df),
        "quality_filters": {
            "labeled_harm_unharm": int(len(labeled)),
            "agreement_available_labeled": int(len(agreement_available)),
            "high_agreement_labeled": int(len(high_agreement)),
            "harmful_label_len_5_220": int(len(harmful_clean)),
            "unharmful_label_len_5_180": int(len(safe_clean)),
            "harmful_high_agreement_len_5_220_eval_grade": int(len(high_agreement_harmful_clean)),
            "harmful_non_bypass_unsafe_candidates": int(len(harmful_non_bypass)),
            "harmful_bypass_jailbreak_candidates": int(len(harmful_bypass)),
            "category_balanced_unsafe_cap_120": int(len(category_balanced_unsafe)),
            "category_balanced_jailbreak_cap_80": int(len(category_balanced_jailbreak)),
        },
        "distributions": {
            "prompt_harm_label": value_counts(df["prompt_harm_label"]),
            "adversarial": value_counts(df["adversarial"]),
            "subcategory_top": value_counts(df["subcategory"], limit=30),
            "harmful_bypass_subcategory_top": value_counts(harmful_bypass["subcategory"], limit=20)
            if len(harmful_bypass)
            else {},
        },
        "recommended_quota_v1": {
            "unsafe": 1200,
            "jailbreak": 300,
        },
        "selection": [
            "Use prompt only.",
            "UNSAFE: prompt_harm_label=harmful, length-filtered, no bypass pattern, stratify by subcategory.",
            "Use prompt_harm_agreement only as optional eval-grade preference because most rows have missing agreement.",
            "JAILBREAK: harmful + bypass pattern, optionally intersect/stratify with adversarial metadata.",
            "Do not label all adversarial rows as JAILBREAK.",
        ],
        "quality_verdict": "high_quality_label_and_pattern_extraction",
    }


def review_jailbreakv() -> dict[str, Any]:
    main_path = download_hf("JailbreakV-28K/JailBreakV-28k", "JailBreakV_28K/JailBreakV_28K.csv")
    red_path = download_hf("JailbreakV-28K/JailBreakV-28k", "JailBreakV_28K/RedTeam_2K.csv")
    df = pd.concat([pd.read_csv(main_path), pd.read_csv(red_path)], ignore_index=True)
    text = df[
        df["format"].fillna("").astype(str).str.lower().isin({"template", "logic", "persuade"})
        & (df["transfer_from_llm"] == True)  # noqa: E712
    ].copy()
    text["prompt"] = text["jailbreak_query"].fillna("").astype(str)
    word_counts = text["prompt"].map(words)
    clean = text[word_counts.between(8, 350)]
    policy_balanced = clean.groupby(["format", "policy"]).head(35)
    return {
        "source": "JailBreakV-28K",
        "role": "JAILBREAK_text_attack",
        "common": prompt_common_stats(text, "prompt"),
        "quality_filters": {
            "text_transfer_template_logic_persuade": int(len(text)),
            "clean_len_8_350_words": int(len(clean)),
            "balanced_cap_35_per_format_policy": int(len(policy_balanced)),
            "unique_policies_clean": int(clean["policy"].nunique()),
            "unique_formats_clean": int(clean["format"].nunique()),
        },
        "distributions": {
            "format_all": value_counts(df["format"]),
            "format_clean": value_counts(clean["format"]),
            "policy_clean_top": value_counts(clean["policy"], limit=25),
            "source_from_clean": value_counts(clean["from"], limit=20),
        },
        "recommended_quota_v1": 900,
        "selection": [
            "Use `jailbreak_query` as router input.",
            "Filter to text methods Template, Logic, Persuade and transfer_from_llm=true.",
            "Stratify by format and policy; avoid image-dependent rows.",
            "Use `redteam_query` only as metadata or separate UNSAFE baseline.",
        ],
        "quality_verdict": "high_quality_attack_metadata_extraction",
    }


def listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return list(value)
    if hasattr(value, "tolist"):
        converted = value.tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def review_multijail() -> dict[str, Any]:
    languages = ["ar", "bn", "en", "it", "jv", "ko", "sw", "th", "vi", "zh"]
    frames = []
    for lang in languages:
        path = download_hf("walledai/MultiJail", f"data/{lang}-00000-of-00001.parquet")
        frame = pd.read_parquet(path)
        frame["language"] = lang
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    prompt = df["prompt"].fillna("").astype(str)
    char_counts = prompt.map(chars)
    clean = df[char_counts.between(8, 1200)]
    language_harm_records = []
    for _, row in clean.iterrows():
        for harm in listish(row["harms"]):
            language_harm_records.append({"language": row["language"], "harm": str(harm)})
    harm_df = pd.DataFrame(language_harm_records)
    balanced = clean.groupby("language").head(90)
    vi = clean[clean["language"] == "vi"]
    return {
        "source": "MultiJail",
        "role": "MULTILINGUAL_UNSAFE_and_eval_slice",
        "common": prompt_common_stats(df),
        "quality_filters": {
            "clean_len_8_1200_chars": int(len(clean)),
            "vietnamese_clean": int(len(vi)),
            "balanced_cap_90_per_language": int(len(balanced)),
            "languages": int(clean["language"].nunique()),
            "language_harm_pairs": int(len(harm_df)),
        },
        "distributions": {
            "language": value_counts(clean["language"], limit=20),
            "harm_top": value_counts(harm_df["harm"], limit=30) if len(harm_df) else {},
            "source": value_counts(clean["source"], limit=10),
        },
        "recommended_quota_v1": {
            "unsafe_multilingual": 500,
            "vietnamese_minimum": 150,
        },
        "selection": [
            "Use base rows as UNSAFE multilingual prompts, not automatic JAILBREAK.",
            "Stratify by language and harm category.",
            "Reserve Vietnamese rows for production-relevant multilingual coverage.",
            "Create jailbreak/code-switch variants only through controlled wrappers.",
        ],
        "quality_verdict": "high_quality_multilingual_stratified_extraction",
    }


def review_beavertails() -> dict[str, Any]:
    path = download_hf("PKU-Alignment/BeaverTails", "round0/30k/train.jsonl.gz")
    rows = read_jsonl(path)
    df = pd.DataFrame(rows)
    prompt = df["prompt"].fillna("").astype(str)
    word_counts = prompt.map(words)
    clean = df[word_counts.between(5, 220)]
    unsafe = clean[clean["is_safe"] == False]  # noqa: E712
    safe = clean[clean["is_safe"] == True]  # noqa: E712
    category_records = []
    for _, row in unsafe.iterrows():
        category = row.get("category")
        if isinstance(category, dict):
            for key, value in category.items():
                if value:
                    category_records.append({"category": key})
    cat_df = pd.DataFrame(category_records)
    balanced_unsafe = unsafe.copy()
    first_category = []
    for category in balanced_unsafe["category"]:
        selected = "<none>"
        if isinstance(category, dict):
            selected = next((key for key, value in category.items() if value), "<none>")
        first_category.append(selected)
    balanced_unsafe["first_category"] = first_category
    balanced_cap = balanced_unsafe.groupby("first_category").head(80)
    return {
        "source": "BeaverTails",
        "role": "OPTIONAL_UNSAFE_SAFE_license_limited",
        "common": prompt_common_stats(df),
        "quality_filters": {
            "clean_len_5_220_words": int(len(clean)),
            "unsafe_clean": int(len(unsafe)),
            "safe_clean": int(len(safe)),
            "balanced_unsafe_cap_80_per_first_category": int(len(balanced_cap)),
            "unique_unsafe_categories": int(cat_df["category"].nunique()) if len(cat_df) else 0,
        },
        "distributions": {
            "is_safe": value_counts(df["is_safe"]),
            "unsafe_category_top": value_counts(cat_df["category"], limit=30) if len(cat_df) else {},
        },
        "recommended_quota_v1": {
            "unsafe": 0,
            "unsafe_if_noncommercial_ok": 300,
        },
        "selection": [
            "Use prompt only, never response.",
            "Filter by is_safe and category; stratify by category.",
            "Use only if CC-BY-NC-4.0 is acceptable for your target use.",
        ],
        "quality_verdict": "quality_extractable_but_license_limited",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviews = [
        review_canttalk(),
        review_clinc(),
        review_wildguard(),
        review_jailbreakv(),
        review_multijail(),
    ]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "excluded": ["EduVidQA", "PolyGuardPrompts", "BeaverTails"],
        "reviews": reviews,
    }
    write_json(OUT_DIR / "deep_review.json", payload)
    flat_rows = []
    for review in reviews:
        row = {
            "source": review["source"],
            "role": review["role"],
            "quality_verdict": review["quality_verdict"],
            "rows": review["common"]["rows"],
            "unique": review["common"]["unique"],
            "duplicates": review["common"]["duplicates"],
            "recommended_quota_v1": json.dumps(review["recommended_quota_v1"], ensure_ascii=False),
        }
        for key, value in review["quality_filters"].items():
            if isinstance(value, int | float | str):
                row[key] = value
        flat_rows.append(row)
    pd.DataFrame(flat_rows).to_csv(OUT_DIR / "deep_review_summary.csv", index=False)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
