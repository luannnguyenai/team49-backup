"""Validate source feasibility for the guardrail-router fine-tuning dataset.

This script intentionally downloads metadata and small samples first, not full
raw datasets. The proposed training mix uses capped subsets, so schema/license
validation should happen before pulling large files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from huggingface_hub import HfApi, hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "guardrail_router" / "source_validation"
HF_DATASET_SERVER = "https://datasets-server.huggingface.co"


@dataclass(frozen=True)
class HFDatasetTarget:
    name: str
    repo_id: str
    expected_columns: tuple[str, ...]
    preferred_splits: tuple[str, ...] = ("train", "test", "validation", "val")


HF_TARGETS = (
    HFDatasetTarget(
        name="wildguardmix",
        repo_id="allenai/wildguardmix",
        expected_columns=(
            "prompt",
            "adversarial",
            "prompt_harm_label",
            "response_harm_label",
            "response_refusal_label",
            "subcategory",
        ),
        preferred_splits=("test", "train"),
    ),
    HFDatasetTarget(
        name="jailbreakv_28k",
        repo_id="JailbreakV-28K/JailBreakV-28k",
        expected_columns=(
            "jailbreak_query",
            "redteam_query",
            "format",
            "policy",
            "transfer_from_llm",
        ),
    ),
    HFDatasetTarget(
        name="canttalkaboutthis",
        repo_id="nvidia/CantTalkAboutThis-Topic-Control-Dataset",
        expected_columns=(
            "domain",
            "scenario",
            "system_instruction",
            "conversation",
            "distractors",
            "conversation_with_distractors",
        ),
    ),
    HFDatasetTarget(
        name="multijail",
        repo_id="walledai/MultiJail",
        expected_columns=(
            "prompt",
            "harms",
            "source",
        ),
        preferred_splits=("vi", "en", "zh", "th", "ko", "ar"),
    ),
    HFDatasetTarget(
        name="beavertails_optional",
        repo_id="PKU-Alignment/BeaverTails",
        expected_columns=(
            "prompt",
            "response",
            "category",
            "is_safe",
        ),
        preferred_splits=("30k_train", "30k_test", "train", "test"),
    ),
    HFDatasetTarget(
        name="polyguardprompts_optional",
        repo_id="ToxicityPrompts/PolyGuardPrompts",
        expected_columns=(
            "prompt",
            "prompt_harm_label",
            "response_harm_label",
            "response_refusal_label",
        ),
        preferred_splits=("train", "test", "validation"),
    ),
)


CLINC_URL_CANDIDATES = (
    "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json",
    "https://raw.githubusercontent.com/clinc/oos-eval/main/data/data_full.json",
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl_sample(path: Path, limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(rows) >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate_local_eduvidqa() -> dict[str, Any]:
    summary_path = ROOT / "data" / "eduvidqa" / "reports" / "dataset_summary.json"
    sample_path = ROOT / "data" / "eduvidqa" / "ft_context_vlm_clean" / "synthetic_train.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    sample_rows = read_jsonl_sample(sample_path)
    columns = sorted(sample_rows[0].keys()) if sample_rows else []
    return {
        "source": "local",
        "path": str(summary_path.relative_to(ROOT)) if summary_path.exists() else None,
        "summary_exists": summary_path.exists(),
        "usable_rows_with_timestamp": summary.get("usable_rows_with_timestamp"),
        "valid_context_samples_window_120": summary.get("valid_context_samples_window_120"),
        "unique_videos_valid": summary.get("unique_videos_valid"),
        "sample_file": str(sample_path.relative_to(ROOT)) if sample_path.exists() else None,
        "sample_columns": columns,
        "sample_rows": sample_rows,
        "feasibility": "usable_for_on_topic" if summary.get("valid_context_samples_window_120", 0) >= 4000 else "needs_review",
    }


def validate_local_question_bank() -> dict[str, Any]:
    path = ROOT / "data" / "final_artifacts" / "cs224n_cs231n_cs230_v1" / "canonical" / "question_bank.jsonl"
    rows = []
    counts = {
        "total": 0,
        "qa_gate_passed": 0,
        "with_primary_kp_id": 0,
        "with_unit_id": 0,
        "with_course_id": 0,
    }
    courses: set[str] = set()
    lectures: set[str] = set()
    units: set[str] = set()

    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                counts["total"] += 1
                if row.get("qa_gate_passed") is True:
                    counts["qa_gate_passed"] += 1
                if row.get("primary_kp_id"):
                    counts["with_primary_kp_id"] += 1
                if row.get("unit_id"):
                    counts["with_unit_id"] += 1
                    units.add(row["unit_id"])
                if row.get("course_id"):
                    counts["with_course_id"] += 1
                    courses.add(row["course_id"])
                if row.get("lecture_id"):
                    lectures.add(row["lecture_id"])
                if len(rows) < 5:
                    rows.append(row)

    return {
        "source": "local",
        "path": str(path.relative_to(ROOT)) if path.exists() else None,
        "exists": path.exists(),
        "counts": counts,
        "unique_courses": sorted(courses),
        "unique_lectures": len(lectures),
        "unique_units": len(units),
        "sample_columns": sorted(rows[0].keys()) if rows else [],
        "sample_rows": rows,
        "feasibility": "usable_for_on_topic_and_cross_pairs"
        if counts["qa_gate_passed"] >= 1000 and counts["with_primary_kp_id"] >= 1000
        else "needs_review",
    }


def requests_get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def pick_split(splits: list[dict[str, Any]], preferred: tuple[str, ...]) -> dict[str, Any] | None:
    if not splits:
        return None
    for split_name in preferred:
        for split in splits:
            if split.get("split") == split_name:
                return split
    return splits[0]


def validate_hf_dataset(target: HFDatasetTarget, api: HfApi) -> dict[str, Any]:
    dataset_dir = OUT_DIR / "hf" / target.name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "source": "huggingface",
        "name": target.name,
        "repo_id": target.repo_id,
        "expected_columns": list(target.expected_columns),
        "metadata_downloaded": False,
        "sample_downloaded": False,
        "errors": [],
    }

    try:
        info = api.dataset_info(target.repo_id)
        siblings = [s.rfilename for s in info.siblings]
        card_data = getattr(info, "card_data", None)
        result.update(
            {
                "sha": info.sha,
                "last_modified": str(info.last_modified) if info.last_modified else None,
                "downloads": info.downloads,
                "likes": info.likes,
                "siblings_count": len(siblings),
                "files_preview": siblings[:50],
                "license": getattr(card_data, "license", None) if card_data else None,
                "tags": getattr(card_data, "tags", None) if card_data else None,
            }
        )
        write_json(dataset_dir / "repo_info.json", result)
        result["metadata_downloaded"] = True

        if "README.md" in siblings:
            readme_path = hf_hub_download(
                repo_id=target.repo_id,
                repo_type="dataset",
                filename="README.md",
                local_dir=dataset_dir,
            )
            result["readme_path"] = str(Path(readme_path).relative_to(ROOT))
    except Exception as exc:  # noqa: BLE001 - report external dataset failures.
        result["errors"].append(f"repo_info: {type(exc).__name__}: {exc}")
        return result

    try:
        split_payload = requests_get_json(f"{HF_DATASET_SERVER}/splits", {"dataset": target.repo_id})
        splits = split_payload.get("splits", [])
        result["splits"] = splits
        chosen_split = pick_split(splits, target.preferred_splits)
        result["chosen_split"] = chosen_split
        if chosen_split:
            rows_payload = requests_get_json(
                f"{HF_DATASET_SERVER}/rows",
                {
                    "dataset": target.repo_id,
                    "config": chosen_split["config"],
                    "split": chosen_split["split"],
                    "offset": 0,
                    "length": 5,
                },
            )
            rows = [item.get("row", {}) for item in rows_payload.get("rows", [])]
            sample_columns = sorted(rows[0].keys()) if rows else []
            missing_columns = sorted(set(target.expected_columns) - set(sample_columns))
            result.update(
                {
                    "sample_downloaded": bool(rows),
                    "sample_columns": sample_columns,
                    "missing_expected_columns_in_sample": missing_columns,
                    "sample_rows": rows,
                    "feasibility": "schema_ok" if not missing_columns else "schema_needs_mapping",
                }
            )
            write_json(dataset_dir / "sample_rows.json", rows)
    except Exception as exc:  # noqa: BLE001 - report external dataset failures.
        result["errors"].append(f"sample_rows: {type(exc).__name__}: {exc}")

    if not result.get("sample_downloaded"):
        try:
            parquet_files = [
                file_name
                for file_name in result.get("files_preview", [])
                if file_name.endswith(".parquet")
            ]
            if not parquet_files and "files_preview" in result:
                full_files = [s.rfilename for s in api.dataset_info(target.repo_id).siblings]
                parquet_files = [file_name for file_name in full_files if file_name.endswith(".parquet")]
            chosen_file = None
            for preferred in target.preferred_splits:
                for file_name in parquet_files:
                    if preferred.lower() in file_name.lower():
                        chosen_file = file_name
                        break
                if chosen_file:
                    break
            chosen_file = chosen_file or (parquet_files[0] if parquet_files else None)
            if chosen_file:
                parquet_path = hf_hub_download(
                    repo_id=target.repo_id,
                    repo_type="dataset",
                    filename=chosen_file,
                    local_dir=dataset_dir,
                )
                frame = pd.read_parquet(parquet_path)
                rows = frame.head(5).to_dict(orient="records")
                sample_columns = sorted(frame.columns.tolist())
                missing_columns = sorted(set(target.expected_columns) - set(sample_columns))
                result.update(
                    {
                        "sample_downloaded": bool(rows),
                        "sample_download_method": "hf_hub_download_parquet",
                        "sample_file": str(Path(parquet_path).relative_to(ROOT)),
                        "sample_columns": sample_columns,
                        "missing_expected_columns_in_sample": missing_columns,
                        "sample_rows": rows,
                        "feasibility": "schema_ok" if not missing_columns else "schema_needs_mapping",
                    }
                )
                if target.name == "multijail" and chosen_file.startswith("data/"):
                    result["derived_language_from_split"] = chosen_file.removeprefix("data/").split("-", 1)[0]
                write_json(dataset_dir / "sample_rows.json", rows)
        except Exception as exc:  # noqa: BLE001 - report external dataset failures.
            result["errors"].append(f"parquet_fallback: {type(exc).__name__}: {exc}")

    write_json(dataset_dir / "validation.json", result)
    return result


def validate_clinc() -> dict[str, Any]:
    out_dir = OUT_DIR / "github" / "clinc_oos_eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "source": "github",
        "name": "clinc_oos_eval",
        "url_candidates": list(CLINC_URL_CANDIDATES),
        "downloaded": False,
        "errors": [],
    }

    for url in CLINC_URL_CANDIDATES:
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 404:
                result["errors"].append(f"404: {url}")
                continue
            response.raise_for_status()
            payload = response.json()
            raw_path = out_dir / "data_full.json"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["downloaded"] = True
            result["url"] = url
            result["raw_path"] = str(raw_path.relative_to(ROOT))
            result["top_level_keys"] = sorted(payload.keys())
            split_counts: dict[str, int] = {}
            for key, value in payload.items():
                if isinstance(value, list):
                    split_counts[key] = len(value)
                elif isinstance(value, dict):
                    split_counts[key] = sum(len(v) for v in value.values() if isinstance(v, list))
            result["split_counts"] = split_counts
            result["sample"] = {
                key: value[:3]
                for key, value in payload.items()
                if isinstance(value, list)
            }
            result["feasibility"] = "usable_for_safe_off_topic" if split_counts else "needs_mapping_review"
            break
        except Exception as exc:  # noqa: BLE001 - report external dataset failures.
            result["errors"].append(f"{url}: {type(exc).__name__}: {exc}")

    write_json(out_dir / "validation.json", result)
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary_rows = []
    for result in results:
        summary_rows.append(
            {
                "name": result.get("name", result.get("source")),
                "source": result.get("source"),
                "feasibility": result.get("feasibility"),
                "sample_downloaded": result.get("sample_downloaded", result.get("downloaded")),
                "errors": result.get("errors", []),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(OUT_DIR.relative_to(ROOT)),
        "results": summary_rows,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    results: list[dict[str, Any]] = []
    results.append({"name": "eduvidqa", **validate_local_eduvidqa()})
    results.append({"name": "question_bank", **validate_local_question_bank()})
    for target in HF_TARGETS:
        results.append(validate_hf_dataset(target, api))
    results.append(validate_clinc())

    summary = summarize(results)
    write_json(OUT_DIR / "summary.json", summary)
    pd.DataFrame(summary["results"]).to_csv(OUT_DIR / "summary.csv", index=False)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
