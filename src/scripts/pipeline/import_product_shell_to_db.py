"""Import product course shell rows into PostgreSQL.

Sources:
- bootstrap `courses.json` and `overviews.json` for catalog metadata
- canonical `units.jsonl` for section/unit hierarchy and canonical links

This keeps the product shell aligned with canonical units while preserving
course-level display metadata from the bootstrap files.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.data_paths import CANONICAL_ARTIFACTS_DIR, COURSES_FILE, OVERVIEWS_FILE
from src.database import async_session
from src.models.course import (
    Course,
    CourseOverview,
    CourseSection,
    CourseSectionKind,
    CourseStatus,
    CourseVisibility,
    LearningUnit,
    LearningUnitEntryMode,
    LearningUnitStatus,
    LearningUnitType,
)

DEFAULT_CANONICAL_UNITS_PATH = CANONICAL_ARTIFACTS_DIR / "units.jsonl"
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "a20-app-049/product-shell")
CHUNK_SIZE = 250


@dataclass(frozen=True)
class ImportSpec:
    model: type
    pk_columns: tuple[str, ...]


IMPORT_SPECS: dict[str, ImportSpec] = {
    "courses": ImportSpec(Course, ("id",)),
    "course_overviews": ImportSpec(CourseOverview, ("id",)),
    "course_sections": ImportSpec(CourseSection, ("id",)),
    "learning_units": ImportSpec(LearningUnit, ("id",)),
}


def _stable_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def canonical_unit_slug(unit_id: str) -> str:
    value = unit_id
    if value.startswith("local::"):
        value = value[len("local::") :]
    value = value.replace("::", "-").replace("_", "-").lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def course_slug_from_canonical_id(course_id: str) -> str:
    return course_id.lower()


def build_product_shell_bundle(
    *,
    canonical_units_path: Path = DEFAULT_CANONICAL_UNITS_PATH,
    courses_path: Path = COURSES_FILE,
    overviews_path: Path = OVERVIEWS_FILE,
) -> dict[str, list[dict[str, Any]]]:
    bootstrap_courses = _read_json(courses_path)
    overview_rows = _read_json(overviews_path)
    canonical_units = _load_jsonl(canonical_units_path)

    course_rows_by_slug = {row["slug"]: row for row in bootstrap_courses}
    overview_by_slug = {row["course_slug"]: row for row in overview_rows}

    courses: list[dict[str, Any]] = []
    course_overviews: list[dict[str, Any]] = []
    course_sections: list[dict[str, Any]] = []
    learning_units: list[dict[str, Any]] = []

    grouped_units: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in canonical_units:
        grouped_units[course_slug_from_canonical_id(row["course_id"])].append(row)

    for course_slug, course_units in sorted(grouped_units.items()):
        bootstrap_course = course_rows_by_slug.get(course_slug)
        if bootstrap_course is None:
            raise ValueError(f"Missing bootstrap course metadata for slug '{course_slug}'")
        bootstrap_overview = overview_by_slug.get(course_slug)
        if bootstrap_overview is None:
            raise ValueError(f"Missing bootstrap overview metadata for slug '{course_slug}'")

        course_id = _stable_uuid("course", course_slug)
        courses.append(
            {
                "id": course_id,
                "slug": course_slug,
                "title": bootstrap_course["title"],
                "short_description": bootstrap_course["short_description"],
                "status": CourseStatus(bootstrap_course["status"]),
                "visibility": CourseVisibility(bootstrap_course.get("visibility", "public")),
                "cover_image_url": bootstrap_course.get("cover_image_url"),
                "hero_badge": bootstrap_course.get("hero_badge"),
                "primary_subject": bootstrap_course.get("primary_subject"),
                "sort_order": bootstrap_course.get("sort_order", 0),
                "canonical_course_id": course_units[0]["course_id"],
            }
        )
        course_overviews.append(
            {
                "id": _stable_uuid("course-overview", course_slug),
                "course_id": course_id,
                "headline": bootstrap_overview["headline"],
                "subheadline": bootstrap_overview.get("subheadline"),
                "summary_markdown": bootstrap_overview["summary_markdown"],
                "learning_outcomes": bootstrap_overview.get("learning_outcomes", []),
                "target_audience": bootstrap_overview.get("target_audience"),
                "prerequisites_summary": bootstrap_overview.get("prerequisites_summary"),
                "estimated_duration_text": bootstrap_overview.get("estimated_duration_text"),
                "structure_snapshot": {
                    "summary": bootstrap_overview.get("structure_snapshot")
                },
                "cta_label": bootstrap_overview.get("cta_label"),
            }
        )

        sections_by_lecture: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
        for unit in course_units:
            key = (unit["lecture_id"], int(unit["lecture_order"]), unit["lecture_title"])
            sections_by_lecture[key].append(unit)

        ordered_sections = sorted(sections_by_lecture.items(), key=lambda item: item[0][1])
        for section_index, (section_key, section_units) in enumerate(ordered_sections, start=1):
            lecture_id, lecture_order, lecture_title = section_key
            section_id = _stable_uuid("section", f"{course_slug}:{lecture_id}")
            course_sections.append(
                {
                    "id": section_id,
                    "course_id": course_id,
                    "parent_section_id": None,
                    "title": lecture_title,
                    "kind": CourseSectionKind.lecture_group,
                    "sort_order": lecture_order,
                    "is_entry_section": section_index == 1,
                }
            )

            sorted_units = sorted(
                section_units,
                key=lambda row: (int(row.get("ordering_index") or 0), row["unit_id"]),
            )
            for unit in sorted_units:
                has_video = bool((unit.get("content_ref") or {}).get("video_url"))
                learning_units.append(
                    {
                        "id": _stable_uuid("learning-unit", unit["unit_id"]),
                        "course_id": course_id,
                        "section_id": section_id,
                        "slug": canonical_unit_slug(unit["unit_id"]),
                        "title": unit.get("unit_name") or unit["unit_id"],
                        "unit_type": LearningUnitType.lesson,
                        "status": LearningUnitStatus.ready,
                        "sort_order": int(unit.get("ordering_index") or 0),
                        "content_source_type": "canonical_unit_summary",
                        "content_body": unit.get("summary") or unit.get("description"),
                        "estimated_minutes": unit.get("duration_min"),
                        "canonical_unit_id": unit["unit_id"],
                        "entry_mode": (
                            LearningUnitEntryMode.hybrid
                            if has_video and (unit.get("summary") or unit.get("description"))
                            else LearningUnitEntryMode.video
                            if has_video
                            else LearningUnitEntryMode.text
                        ),
                    }
                )

    return {
        "courses": courses,
        "course_overviews": course_overviews,
        "course_sections": course_sections,
        "learning_units": learning_units,
    }


def _validate_rows(table_name: str, rows: list[dict[str, Any]], spec: ImportSpec) -> None:
    known_columns = set(spec.model.__table__.columns.keys())
    for index, row in enumerate(rows):
        unknown = set(row) - known_columns
        if unknown:
            raise ValueError(f"{table_name}[{index}] has unknown columns: {sorted(unknown)}")
        missing_pk = [column for column in spec.pk_columns if row.get(column) in (None, "")]
        if missing_pk:
            raise ValueError(f"{table_name}[{index}] missing primary key columns: {missing_pk}")


def conflict_columns_for_table(table_name: str) -> tuple[str, ...]:
    if table_name == "courses":
        return ("slug",)
    if table_name == "course_overviews":
        return ("course_id",)
    if table_name == "learning_units":
        return ("course_id", "slug")
    return IMPORT_SPECS[table_name].pk_columns


def _chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


async def _import_table(
    session: AsyncSession,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    spec: ImportSpec,
) -> int:
    _validate_rows(table_name, rows, spec)
    if not rows:
        return 0

    update_columns = [
        column.name
        for column in spec.model.__table__.columns
        if column.name not in spec.pk_columns and column.name not in {"created_at"}
    ]
    imported = 0
    for chunk in _chunks(rows, CHUNK_SIZE):
        stmt = pg_insert(spec.model).values(chunk)
        excluded = stmt.excluded
        update_values = {
            column: getattr(excluded, column)
            for column in update_columns
            if column != "updated_at"
        }
        if "updated_at" in update_columns:
            update_values["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=list(conflict_columns_for_table(table_name)),
            set_=update_values,
        )
        await session.execute(stmt)
        imported += len(chunk)
    await session.flush()
    return imported


async def import_product_shell(
    session: AsyncSession,
    *,
    canonical_units_path: Path = DEFAULT_CANONICAL_UNITS_PATH,
    courses_path: Path = COURSES_FILE,
    overviews_path: Path = OVERVIEWS_FILE,
) -> dict[str, Any]:
    bundle = build_product_shell_bundle(
        canonical_units_path=canonical_units_path,
        courses_path=courses_path,
        overviews_path=overviews_path,
    )
    imported: dict[str, int] = {}
    for table_name, rows in bundle.items():
        imported[table_name] = await _import_table(
            session,
            table_name=table_name,
            rows=rows,
            spec=IMPORT_SPECS[table_name],
        )
    return {
        "counts": {key: len(rows) for key, rows in bundle.items()},
        "imported": imported,
    }


async def _run(*, validate_only: bool) -> dict[str, Any]:
    bundle = build_product_shell_bundle()
    if validate_only:
        return {"counts": {key: len(rows) for key, rows in bundle.items()}}

    async with async_session() as session:
        result = await import_product_shell(session)
        await session.commit()
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Import product course shell rows into PostgreSQL.")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(validate_only=args.validate_only)), indent=2, default=str))


if __name__ == "__main__":
    main()
