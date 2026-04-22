"""Build lean Prompt 2 input artifacts from sanitized P1 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

P2Mode = Literal["batch_initial", "append_incremental"]

_TIMESTAMP_PATTERN = re.compile(r"\[ts=\d+s\]")
_LECTURE_ID_PATTERN = re.compile(r"lecture[\s_\-:]*0*(\d+)", re.IGNORECASE)
_TUTORIAL_ID_PATTERN = re.compile(r"tutorial[\s_\-:]*0*(\d+)", re.IGNORECASE)
_LOCAL_ID_PATTERN = re.compile(r"^local::([^:]+)::")
_P1_LECTURE_FILE_PATTERN = re.compile(r"^L(\d+)_p1$", re.IGNORECASE)
_P1_SUPP_FILE_PATTERN = re.compile(r"^Lsup_([a-z0-9_]+)_p1$", re.IGNORECASE)

_FALLBACK_TEMPLATE = """SYSTEM:
You are preparing Prompt 2 concept normalization input.

LOCAL_CONCEPTS_KP:
<all_local_kps>

LOCAL_UNIT_KP_MAP:
<all_local_map>

COURSE_METADATA:
<course_metadata>

FROZEN_TAG_REGISTRY:
<frozen_tag_registry>

EXISTING_GLOBALS:
<existing_globals>

EXISTING_EDGES:
<existing_edges>
"""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _infer_track(course_id: str) -> str | None:
    lowered = course_id.lower()
    if "231" in lowered or "cv" in lowered or "vision" in lowered:
        return "cv"
    if "224" in lowered or "nlp" in lowered or lowered.endswith("n"):
        return "nlp"
    if "229" in lowered or "ml" in lowered:
        return "ml"
    if "genai" in lowered or "llm" in lowered:
        return "genai"
    return None


def _extract_local_token(raw_id: str | None) -> str | None:
    if not raw_id:
        return None
    match = _LOCAL_ID_PATTERN.match(raw_id)
    if not match:
        return None
    return match.group(1)


def _slugify(value: str, *, separator: str = "-") -> str:
    collapsed = re.sub(r"[^a-z0-9]+", separator, value.casefold()).strip(separator)
    return re.sub(rf"{re.escape(separator)}+", separator, collapsed)


def _normalize_tag(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = _slugify(value, separator="_")
    return normalized or None


def _normalize_tag_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for raw in values:
        item = _normalize_tag(raw)
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _normalize_difficulty_level(value: Any) -> float | None:
    if not isinstance(value, int | float):
        return None
    number = float(value)
    if number > 1.0:
        number = number / 5.0
    number = max(0.0, min(1.0, number))
    return round(number, 4)


def _extract_video_token(path: Path) -> tuple[tuple[str, int] | None, str]:
    stem = path.stem
    lecture_match = _LECTURE_ID_PATTERN.search(stem)
    if lecture_match:
        number = int(lecture_match.group(1))
        suffix = _slugify(stem[lecture_match.end() :], separator="-")
        token = f"lecture{number:02d}" + (f"-{suffix}" if suffix else "")
        return ("lecture", number), token

    tutorial_match = _TUTORIAL_ID_PATTERN.search(stem)
    if tutorial_match:
        number = int(tutorial_match.group(1))
        suffix = _slugify(stem[tutorial_match.end() :], separator="-")
        token = f"tutorial{number:02d}" + (f"-{suffix}" if suffix else "")
        return ("tutorial", number), token

    return None, _slugify(stem, separator="-")


def _build_video_token_lookup(course_dir: Path) -> dict[tuple[str, int], str]:
    videos_dir = course_dir / "videos"
    lookup: dict[tuple[str, int], str] = {}
    if not videos_dir.exists():
        return lookup

    for path in sorted(videos_dir.glob("*"), key=_parse_video_order):
        key, token = _extract_video_token(path)
        if key is not None and key not in lookup:
            lookup[key] = token
    return lookup


def _resolve_placeholder_lecture_id(
    *,
    artifact: dict[str, Any],
    source_file: Path,
    video_lookup: dict[tuple[str, int], str],
) -> str | None:
    title = artifact.get("lecture_title")
    if isinstance(title, str):
        lecture_match = _LECTURE_ID_PATTERN.search(title)
        if lecture_match:
            token = video_lookup.get(("lecture", int(lecture_match.group(1))))
            if token:
                return token

        tutorial_match = _TUTORIAL_ID_PATTERN.search(title)
        if tutorial_match:
            token = video_lookup.get(("tutorial", int(tutorial_match.group(1))))
            if token:
                return token

    lecture_file_match = _P1_LECTURE_FILE_PATTERN.match(source_file.stem)
    if lecture_file_match:
        token = video_lookup.get(("lecture", int(lecture_file_match.group(1))))
        if token:
            return token

    supp_file_match = _P1_SUPP_FILE_PATTERN.match(source_file.stem)
    if supp_file_match:
        suffix = _slugify(supp_file_match.group(1), separator="-")
        for token in video_lookup.values():
            if suffix and suffix in token:
                return token

    return None


def _repair_identifier(value: Any, *, source_lecture_id: str) -> Any:
    if not isinstance(value, str):
        return value
    if "<lecture_id>" in value:
        return value.replace("<lecture_id>", source_lecture_id)
    return value


def _repair_units(units: list[dict[str, Any]], *, source_lecture_id: str, source_course_id: str) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for unit in units:
        copy = dict(unit)
        copy["unit_id"] = _repair_identifier(copy.get("unit_id"), source_lecture_id=source_lecture_id)
        if copy.get("course_id") == "<course_id>":
            copy["course_id"] = source_course_id
        repaired.append(copy)
    return repaired


def _repair_kps(concepts: list[dict[str, Any]], *, source_lecture_id: str) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for kp in concepts:
        copy = dict(kp)
        copy["local_kp_id"] = _repair_identifier(copy.get("local_kp_id"), source_lecture_id=source_lecture_id)
        repaired.append(copy)
    return repaired


def _repair_maps(mappings: list[dict[str, Any]], *, source_lecture_id: str) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for mapping in mappings:
        copy = dict(mapping)
        copy["unit_id"] = _repair_identifier(copy.get("unit_id"), source_lecture_id=source_lecture_id)
        copy["local_kp_id"] = _repair_identifier(copy.get("local_kp_id"), source_lecture_id=source_lecture_id)
        repaired.append(copy)
    return repaired


def _derive_source_lecture_id(
    artifact: dict[str, Any],
    source_file: Path,
    *,
    video_lookup: dict[tuple[str, int], str],
) -> str:
    lecture_id = artifact.get("lecture_id")
    if isinstance(lecture_id, str) and lecture_id.strip() and "<lecture_id>" not in lecture_id:
        return lecture_id.strip()

    for collection_name, key_name in (("units", "unit_id"), ("concepts_kp_local", "local_kp_id")):
        collection = artifact.get(collection_name)
        if isinstance(collection, list) and collection:
            first = collection[0]
            if isinstance(first, dict):
                token = _extract_local_token(first.get(key_name))
                if token and "<lecture_id>" not in token:
                    return token

    repaired = _resolve_placeholder_lecture_id(artifact=artifact, source_file=source_file, video_lookup=video_lookup)
    if repaired:
        return repaired

    return source_file.stem.removesuffix("_p1")


def _parse_video_order(path: Path) -> tuple[int, int, str]:
    stem = path.stem
    lecture_match = _LECTURE_ID_PATTERN.search(stem)
    if lecture_match:
        return (0, int(lecture_match.group(1)), stem.casefold())

    tutorial_match = _TUTORIAL_ID_PATTERN.search(stem)
    if tutorial_match:
        return (1, int(tutorial_match.group(1)), stem.casefold())

    return (2, 10**9, stem.casefold())


def _normalize_video_label(path: Path) -> str:
    stem = path.stem
    lecture_match = _LECTURE_ID_PATTERN.search(stem)
    if lecture_match:
        return f"lecture-{int(lecture_match.group(1))}"

    tutorial_match = _TUTORIAL_ID_PATTERN.search(stem)
    if tutorial_match:
        return f"tutorial-{int(tutorial_match.group(1))}"

    return re.sub(r"[^a-z0-9]+", "-", stem.casefold()).strip("-")


def _build_course_metadata(course_dir: Path) -> dict[str, Any]:
    videos_dir = course_dir / "videos"
    video_files = sorted(videos_dir.glob("*"), key=_parse_video_order) if videos_dir.exists() else []

    return {
        "id": course_dir.name,
        "name": course_dir.name,
        "track": _infer_track(course_dir.name),
        "lecture_order": [_normalize_video_label(path) for path in video_files],
    }


def _project_local_kp(kp: dict[str, Any], *, source_course_id: str, source_lecture_id: str) -> dict[str, Any]:
    return {
        "local_kp_id": kp.get("local_kp_id"),
        "name": kp.get("name"),
        "description": kp.get("description"),
        "track_tags": _normalize_tag_list(kp.get("track_tags", [])),
        "domain_tags": _normalize_tag_list(kp.get("domain_tags", [])),
        "career_path_tags": _normalize_tag_list(kp.get("career_path_tags", [])),
        "importance_level": kp.get("importance_level"),
        "structural_role": kp.get("structural_role"),
        "difficulty_level": _normalize_difficulty_level(kp.get("difficulty_level")),
        "source_course_id": source_course_id,
        "source_lecture_id": source_lecture_id,
    }


def _project_local_map(mapping: dict[str, Any]) -> dict[str, Any]:
    return {
        "unit_id": mapping.get("unit_id"),
        "local_kp_id": mapping.get("local_kp_id"),
        "planner_role": mapping.get("planner_role"),
        "coverage_level": mapping.get("coverage_level"),
    }


def _validate_artifact_contract(
    *,
    source_file: Path,
    units: list[dict[str, Any]],
    local_kps: list[dict[str, Any]],
    local_maps: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    known_local_kp_ids = {
        row.get("local_kp_id")
        for row in local_kps
        if isinstance(row.get("local_kp_id"), str) and row.get("local_kp_id")
    }

    unit_ids = [unit.get("unit_id") for unit in units if isinstance(unit.get("unit_id"), str)]
    unit_to_roles: dict[str, list[str]] = {}
    for row in local_maps:
        unit_id = row.get("unit_id")
        local_kp_id = row.get("local_kp_id")
        if isinstance(local_kp_id, str) and local_kp_id not in known_local_kp_ids:
            errors.append(f"{source_file.name}: orphan local_kp_id `{local_kp_id}` in local_unit_kp_map")
        if isinstance(unit_id, str):
            unit_to_roles.setdefault(unit_id, []).append(str(row.get("planner_role")))

    for unit_id in unit_ids:
        roles = unit_to_roles.get(unit_id, [])
        if "main" not in roles:
            errors.append(f"{source_file.name}: unit `{unit_id}` missing planner_role=main")

    for unit in units:
        unit_id = unit.get("unit_id", "<unknown>")
        summary = unit.get("summary")
        timestamp_count = len(_TIMESTAMP_PATTERN.findall(summary)) if isinstance(summary, str) else 0
        if timestamp_count < 2:
            errors.append(f"{source_file.name}: unit `{unit_id}` summary must contain at least 2 timestamps")

    return errors


def _read_template(template_file: Path | None) -> str:
    if template_file is None:
        return _FALLBACK_TEMPLATE
    return template_file.read_text(encoding="utf-8")


def _default_output_dir(run_id: str) -> Path:
    return Path("data") / "artifacts" / "p2" / "input" / run_id


def _dedupe_local_kps(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    deduped: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for row in rows:
        local_kp_id = row.get("local_kp_id")
        if not isinstance(local_kp_id, str) or not local_kp_id:
            errors.append("Encountered local_concepts_kp row without a valid local_kp_id")
            continue
        existing = deduped.get(local_kp_id)
        if existing is None:
            deduped[local_kp_id] = row
            continue
        if existing != row:
            errors.append(f"Conflicting duplicate local_kp_id `{local_kp_id}`")
    return list(deduped.values()), errors


def _dedupe_local_maps(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    errors: list[str] = []
    for row in rows:
        unit_id = row.get("unit_id")
        local_kp_id = row.get("local_kp_id")
        if not isinstance(unit_id, str) or not isinstance(local_kp_id, str) or not unit_id or not local_kp_id:
            errors.append("Encountered local_unit_kp_map row without valid unit_id/local_kp_id")
            continue
        key = (unit_id, local_kp_id)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = row
            continue
        if existing != row:
            errors.append(f"Conflicting duplicate local_unit_kp_map row for unit `{unit_id}` and kp `{local_kp_id}`")
    return list(deduped.values()), errors


def build_p2_input(
    *,
    course_dirs: list[Path],
    output_dir: Path,
    run_id: str,
    p2_mode: P2Mode,
    snapshot_dir: Path | None = None,
    tag_registry_file: Path | None = None,
    template_file: Path | None = None,
) -> dict[str, Any]:
    if p2_mode == "append_incremental" and snapshot_dir is None:
        raise ValueError("append_incremental mode requires snapshot_dir")

    local_kps: list[dict[str, Any]] = []
    local_maps: list[dict[str, Any]] = []
    course_metadata: list[dict[str, Any]] = []
    source_files: list[str] = []
    validation_errors: list[str] = []

    for course_dir in course_dirs:
        processed_dir = course_dir / "processed_sanitized"
        if not processed_dir.exists():
            raise ValueError(f"Missing processed_sanitized directory: {processed_dir}")

        video_lookup = _build_video_token_lookup(course_dir)
        course_metadata.append(_build_course_metadata(course_dir))
        for source_file in sorted(processed_dir.glob("*_p1.json")):
            artifact = _load_json(source_file)
            source_files.append(str(source_file))
            source_course_id = course_dir.name
            source_lecture_id = _derive_source_lecture_id(
                artifact,
                source_file,
                video_lookup=video_lookup,
            )

            units = _repair_units(
                [row for row in artifact.get("units", []) if isinstance(row, dict)],
                source_lecture_id=source_lecture_id,
                source_course_id=source_course_id,
            )
            concepts = _repair_kps(
                [row for row in artifact.get("concepts_kp_local", []) if isinstance(row, dict)],
                source_lecture_id=source_lecture_id,
            )
            mappings = _repair_maps(
                [row for row in artifact.get("unit_kp_map_local", []) if isinstance(row, dict)],
                source_lecture_id=source_lecture_id,
            )
            projected_kps = [
                _project_local_kp(
                    row,
                    source_course_id=source_course_id,
                    source_lecture_id=source_lecture_id,
                )
                for row in concepts
            ]
            projected_maps = [
                _project_local_map(row)
                for row in mappings
            ]

            validation_errors.extend(
                _validate_artifact_contract(
                    source_file=source_file,
                    units=units,
                    local_kps=projected_kps,
                    local_maps=projected_maps,
                )
            )
            local_kps.extend(projected_kps)
            local_maps.extend(projected_maps)

    local_kps, dedupe_kp_errors = _dedupe_local_kps(local_kps)
    local_maps, dedupe_map_errors = _dedupe_local_maps(local_maps)
    validation_errors.extend(dedupe_kp_errors)
    validation_errors.extend(dedupe_map_errors)

    if validation_errors:
        raise ValueError("\n".join(validation_errors))

    tag_registry: list[Any]
    if tag_registry_file is not None and tag_registry_file.exists():
        raw = _load_json(tag_registry_file)
        tag_registry = raw if isinstance(raw, list) else []
    else:
        tag_registry = []

    existing_global_catalog: list[dict[str, Any]] = []
    existing_edge_catalog: list[dict[str, Any]] = []
    if p2_mode == "append_incremental":
        assert snapshot_dir is not None
        existing_global_catalog = _load_jsonl(snapshot_dir / "concepts_kp_global.jsonl")
        existing_edge_catalog = _load_jsonl(snapshot_dir / "prerequisite_edges.jsonl")

    course_registry = {
        "p2_mode": p2_mode,
        "batch_id": run_id,
        "run_id": run_id,
        "courses": course_metadata,
        "source_files": source_files,
    }

    bundle: dict[str, Any] = {
        "local_concepts_kp": local_kps,
        "local_unit_kp_map": local_maps,
        "course_registry": course_registry,
        "tag_registry": tag_registry,
    }
    if p2_mode == "append_incremental":
        bundle["existing_global_catalog"] = existing_global_catalog
        bundle["existing_edge_catalog"] = existing_edge_catalog

    output_dir.mkdir(parents=True, exist_ok=True)
    _dump_json(output_dir / "p2_input_bundle.json", bundle)

    template = _read_template(template_file)
    rendered = (
        template.replace("<all_local_kps>", json.dumps(local_kps, ensure_ascii=False))
        .replace("<all_local_map>", json.dumps(local_maps, ensure_ascii=False))
        .replace("<course_metadata>", json.dumps(course_registry, ensure_ascii=False))
        .replace("<frozen_tag_registry>", json.dumps(tag_registry, ensure_ascii=False))
        .replace("<existing_globals>", json.dumps(existing_global_catalog, ensure_ascii=False))
        .replace("<existing_edges>", json.dumps(existing_edge_catalog, ensure_ascii=False))
    )
    input_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    (output_dir / "prompt_rendered.txt").write_text(rendered, encoding="utf-8")

    return {
        "summary": {
            "status": "ok",
            "run_id": run_id,
            "local_concepts_kp": len(local_kps),
            "local_unit_kp_map": len(local_maps),
            "courses": len(course_metadata),
        },
        "output_dir": str(output_dir),
        "input_hash": input_hash,
    }


def main(
    *,
    course_dirs: list[Path],
    output_dir: Path | None,
    run_id: str | None,
    p2_mode: P2Mode,
    snapshot_dir: Path | None,
    tag_registry_file: Path | None,
    template_file: Path | None,
) -> None:
    resolved_run_id = run_id or datetime.now(UTC).strftime("p2_%Y%m%d_%H%M%S")
    resolved_output_dir = output_dir or _default_output_dir(resolved_run_id)
    report = build_p2_input(
        course_dirs=course_dirs,
        output_dir=resolved_output_dir,
        run_id=resolved_run_id,
        p2_mode=p2_mode,
        snapshot_dir=snapshot_dir,
        tag_registry_file=tag_registry_file,
        template_file=template_file,
    )
    print(json.dumps(report["summary"], ensure_ascii=False))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build lean Prompt 2 input artifacts from sanitized P1 outputs.")
    parser.add_argument("--course-dir", action="append", required=True, dest="course_dirs")
    parser.add_argument("--output-dir")
    parser.add_argument("--run-id")
    parser.add_argument("--p2-mode", choices=["batch_initial", "append_incremental"], default="batch_initial")
    parser.add_argument("--snapshot-dir")
    parser.add_argument("--tag-registry-file")
    parser.add_argument("--template-file")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    main(
        course_dirs=[Path(raw) for raw in args.course_dirs],
        output_dir=Path(args.output_dir) if args.output_dir else None,
        run_id=args.run_id,
        p2_mode=args.p2_mode,
        snapshot_dir=Path(args.snapshot_dir) if args.snapshot_dir else None,
        tag_registry_file=Path(args.tag_registry_file) if args.tag_registry_file else None,
        template_file=Path(args.template_file) if args.template_file else None,
    )
