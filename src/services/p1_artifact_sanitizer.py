from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

_P1_REQUIRED_KEYS = (
    "lecture_title",
    "table_of_contents",
    "units",
    "concepts_kp_local",
    "unit_kp_map_local",
    "section_flags",
    "self_critique_trace",
)
_URL_PATTERN = re.compile(r"https?://[^\s\]]+")


def _issue(*, code: str, path: str, message: str, value: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "path": path,
        "message": message,
    }
    if value is not None:
        payload["value"] = value
    return payload


def _extract_url(raw: str) -> str | None:
    match = _URL_PATTERN.search(raw)
    if not match:
        return None
    return match.group(0).rstrip("),")


def _sanitize_unit(unit: dict[str, Any], *, unit_index: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sanitized = deepcopy(unit)
    issues: list[dict[str, Any]] = []

    weird_template_keys = [
        key for key in list(sanitized.keys()) if key != "is_template" and "is_template" in key
    ]
    if weird_template_keys:
        if "is_template" not in sanitized:
            recovered = next(
                (sanitized[key] for key in weird_template_keys if isinstance(sanitized[key], bool)),
                None,
            )
            if isinstance(recovered, bool):
                sanitized["is_template"] = recovered
                issues.append(
                    _issue(
                        code="unit_is_template_key_recovered",
                        path=f"units[{unit_index}].is_template",
                        message="Recovered is_template from a malformed unit key.",
                    )
                )
        for key in weird_template_keys:
            sanitized.pop(key, None)

    content_ref = sanitized.get("content_ref")
    if isinstance(content_ref, dict):
        raw_video_url = content_ref.get("video_url")
        if isinstance(raw_video_url, str):
            clean_video_url = _extract_url(raw_video_url.strip())
            if clean_video_url and clean_video_url != raw_video_url:
                content_ref["video_url"] = clean_video_url
                issues.append(
                    _issue(
                        code="unit_video_url_sanitized",
                        path=f"units[{unit_index}].content_ref.video_url",
                        message="Sanitized malformed video_url string.",
                        value=clean_video_url,
                    )
                )

    return sanitized, issues


def _validate_artifact(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for key in _P1_REQUIRED_KEYS:
        if key not in artifact:
            issues.append(
                _issue(
                    code="missing_top_level_key",
                    path=key,
                    message="Required top-level key is missing from the P1 artifact.",
                )
            )

    units = artifact.get("units")
    if not isinstance(units, list):
        issues.append(
            _issue(
                code="invalid_units_collection",
                path="units",
                message="units must be a list.",
                value=type(units).__name__,
            )
        )
        return issues

    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            issues.append(
                _issue(
                    code="invalid_unit_record",
                    path=f"units[{index}]",
                    message="Each unit must be a JSON object.",
                    value=type(unit).__name__,
                )
            )
            continue

        for required_key in ("unit_id", "content_ref", "is_template"):
            if required_key not in unit:
                issues.append(
                    _issue(
                        code="missing_unit_key",
                        path=f"units[{index}].{required_key}",
                        message="Required unit key is missing after sanitization.",
                    )
                )

        if "is_template" in unit and not isinstance(unit["is_template"], bool):
            issues.append(
                _issue(
                    code="invalid_is_template_type",
                    path=f"units[{index}].is_template",
                    message="is_template must be a boolean.",
                    value=type(unit["is_template"]).__name__,
                )
            )

        content_ref = unit.get("content_ref")
        if not isinstance(content_ref, dict):
            issues.append(
                _issue(
                    code="invalid_content_ref",
                    path=f"units[{index}].content_ref",
                    message="content_ref must be an object.",
                    value=type(content_ref).__name__,
                )
            )
            continue

        video_url = content_ref.get("video_url")
        if not isinstance(video_url, str) or not video_url.startswith(("http://", "https://")):
            issues.append(
                _issue(
                    code="invalid_video_url",
                    path=f"units[{index}].content_ref.video_url",
                    message="video_url must be an absolute http(s) URL after sanitization.",
                    value=video_url,
                )
            )

        for time_key in ("start_s", "end_s"):
            value = content_ref.get(time_key)
            if not isinstance(value, int | float):
                issues.append(
                    _issue(
                        code="invalid_content_ref_time",
                        path=f"units[{index}].content_ref.{time_key}",
                        message=f"{time_key} must be numeric.",
                        value=value,
                    )
                )

    return issues


def sanitize_p1_artifacts(*, input_dir: Path, output_dir: Path) -> dict[str, Any]:
    files_report: list[dict[str, Any]] = []
    processed_files = 0
    sanitized_files = 0
    invalid_files = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in sorted(input_dir.glob("*_p1.json")):
        processed_files += 1
        issues: list[dict[str, Any]] = []

        raw_text = input_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            invalid_files += 1
            files_report.append(
                {
                    "input_path": str(input_path),
                    "output_path": str(output_dir / input_path.name),
                    "status": "invalid",
                    "issues": [
                        _issue(
                            code="invalid_json",
                            path="$",
                            message="P1 artifact file is empty.",
                        )
                    ],
                }
            )
            continue

        try:
            artifact = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            invalid_files += 1
            files_report.append(
                {
                    "input_path": str(input_path),
                    "output_path": str(output_dir / input_path.name),
                    "status": "invalid",
                    "issues": [
                        _issue(
                            code="invalid_json",
                            path=f"line {exc.lineno}:{exc.colno}",
                            message="P1 artifact file is not valid JSON.",
                            value=str(exc),
                        )
                    ],
                }
            )
            continue

        sanitized = deepcopy(artifact)
        units = sanitized.get("units")
        if isinstance(units, list):
            sanitized_units: list[dict[str, Any]] = []
            for index, unit in enumerate(units):
                if isinstance(unit, dict):
                    clean_unit, unit_issues = _sanitize_unit(unit, unit_index=index)
                    sanitized_units.append(clean_unit)
                    issues.extend(unit_issues)
                else:
                    sanitized_units.append(unit)
            sanitized["units"] = sanitized_units

        issues.extend(_validate_artifact(sanitized))
        output_path = output_dir / input_path.name

        if any(issue["code"] not in {"unit_video_url_sanitized", "unit_is_template_key_recovered"} for issue in issues):
            invalid_files += 1
            files_report.append(
                {
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "status": "invalid",
                    "issues": issues,
                }
            )
            continue

        output_path.write_text(
            json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if issues:
            sanitized_files += 1
            status = "sanitized"
        else:
            status = "copied"

        files_report.append(
            {
                "input_path": str(input_path),
                "output_path": str(output_path),
                "status": status,
                "issues": issues,
            }
        )

    return {
        "summary": {
            "processed_files": processed_files,
            "sanitized_files": sanitized_files,
            "invalid_files": invalid_files,
        },
        "files": files_report,
    }

