"""Import canonical JSONL artifacts into the canonical content DB tables.

The importer is intentionally idempotent: every table uses the deterministic
natural key from the artifact bundle as its upsert key.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.data_paths import CANONICAL_ARTIFACTS_DIR
from src.database import async_session
from src.models.canonical import (
    CanonicalUnit,
    ConceptKP,
    ItemCalibration,
    ItemKPMap,
    ItemPhaseMap,
    PrerequisiteEdge,
    PrunedEdge,
    QuestionBankItem,
    UnitKPMap,
)

DEFAULT_INPUT_DIR = CANONICAL_ARTIFACTS_DIR
CHUNK_SIZE = 500
_ORDINAL_SCORE_MAP = {"high": 1.0, "medium": 0.8, "low": 0.6}


@dataclass(frozen=True)
class ImportSpec:
    model: type
    filename: str
    pk_columns: tuple[str, ...]


IMPORT_SPECS: dict[str, ImportSpec] = {
    "concepts_kp": ImportSpec(ConceptKP, "concepts_kp.jsonl", ("kp_id",)),
    "units": ImportSpec(CanonicalUnit, "units.jsonl", ("unit_id",)),
    "unit_kp_map": ImportSpec(UnitKPMap, "unit_kp_map.jsonl", ("unit_id", "kp_id")),
    "question_bank": ImportSpec(QuestionBankItem, "question_bank.jsonl", ("item_id",)),
    "item_calibration": ImportSpec(ItemCalibration, "item_calibration.jsonl", ("item_id",)),
    "item_phase_map": ImportSpec(ItemPhaseMap, "item_phase_map.jsonl", ("item_id", "phase")),
    "item_kp_map": ImportSpec(ItemKPMap, "item_kp_map.jsonl", ("item_id", "kp_id", "kp_role")),
    "prerequisite_edges": ImportSpec(
        PrerequisiteEdge,
        "prerequisite_edges.jsonl",
        ("source_kp_id", "target_kp_id"),
    ),
    "pruned_edges": ImportSpec(
        PrunedEdge,
        "pruned_edges.jsonl",
        ("source_kp_id", "target_kp_id"),
    ),
}


def expected_count_keys() -> list[str]:
    return list(IMPORT_SPECS.keys())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        rows.append(row)
    return rows


def load_manifest(input_dir: Path) -> dict[str, Any]:
    path = input_dir / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_rows(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if table_name != "item_phase_map":
        return rows

    normalized: list[dict[str, Any]] = []
    for row in rows:
        next_row = dict(row)
        suitability_score = next_row.get("suitability_score")
        if isinstance(suitability_score, str):
            mapped = _ORDINAL_SCORE_MAP.get(suitability_score.strip().lower())
            if mapped is None:
                raise ValueError(
                    f"item_phase_map suitability_score has unsupported value: {suitability_score!r}"
                )
            next_row["suitability_score"] = mapped
        normalized.append(next_row)
    return normalized


def validate_rows(table_name: str, rows: list[dict[str, Any]], spec: ImportSpec) -> None:
    known_columns = set(spec.model.__table__.columns.keys())
    for index, row in enumerate(rows):
        unknown = set(row) - known_columns
        if unknown:
            raise ValueError(
                f"{table_name}[{index}] has unknown columns: {sorted(unknown)}"
            )
        missing_pk = [column for column in spec.pk_columns if row.get(column) in (None, "")]
        if missing_pk:
            raise ValueError(
                f"{table_name}[{index}] missing primary key columns: {missing_pk}"
            )


def _chunks(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


async def import_table(
    session: AsyncSession,
    table_name: str,
    rows: list[dict[str, Any]],
    spec: ImportSpec,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> int:
    validate_rows(table_name, rows, spec)
    if not rows:
        return 0

    update_columns = [
        column.name
        for column in spec.model.__table__.columns
        if column.name not in spec.pk_columns and column.name not in {"created_at"}
    ]
    imported = 0
    for chunk in _chunks(rows, chunk_size):
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
            index_elements=list(spec.pk_columns),
            set_=update_values,
        )
        await session.execute(stmt)
        imported += len(chunk)
    await session.flush()
    return imported


def _check_manifest_counts(
    manifest: dict[str, Any],
    loaded_counts: dict[str, int],
) -> None:
    manifest_counts = manifest.get("counts")
    if not isinstance(manifest_counts, dict):
        raise ValueError("manifest missing counts object")
    for key in expected_count_keys():
        expected = manifest_counts.get(key)
        actual = loaded_counts.get(key)
        if expected != actual:
            raise ValueError(
                f"count mismatch for {key}: manifest={expected} loaded={actual}"
            )


async def import_canonical_artifacts(
    session: AsyncSession,
    input_dir: Path = DEFAULT_INPUT_DIR,
    *,
    verify_db_counts: bool = True,
) -> dict[str, Any]:
    validation = validate_canonical_artifacts(input_dir)
    loaded = validation.pop("_loaded_rows")

    imported: dict[str, int] = {}
    for table_name, spec in IMPORT_SPECS.items():
        imported[table_name] = await import_table(
            session=session,
            table_name=table_name,
            rows=loaded[table_name],
            spec=spec,
        )

    db_counts: dict[str, int] | None = None
    if verify_db_counts:
        db_counts = await verify_table_counts(
            session=session,
            expected_counts=validation["counts"],
        )

    return {
        "input_dir": str(input_dir),
        "counts": validation["counts"],
        "imported": imported,
        "db_counts": db_counts,
    }


async def verify_table_counts(
    session: AsyncSession,
    expected_counts: dict[str, int],
) -> dict[str, int]:
    db_counts: dict[str, int] = {}
    for table_name, spec in IMPORT_SPECS.items():
        result = await session.execute(select(func.count()).select_from(spec.model))
        count = int(result.scalar_one())
        db_counts[table_name] = count
        expected = expected_counts.get(table_name)
        if expected != count:
            raise ValueError(
                f"DB count mismatch for {table_name}: expected={expected} db={count}"
            )
    return db_counts


def validate_canonical_artifacts(input_dir: Path = DEFAULT_INPUT_DIR) -> dict[str, Any]:
    manifest = load_manifest(input_dir)
    loaded: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}

    for table_name, spec in IMPORT_SPECS.items():
        rows = load_jsonl(input_dir / spec.filename)
        rows = normalize_rows(table_name, rows)
        validate_rows(table_name, rows, spec)
        loaded[table_name] = rows
        counts[table_name] = len(rows)

    _check_manifest_counts(manifest, counts)

    return {
        "input_dir": str(input_dir),
        "counts": counts,
        "_loaded_rows": loaded,
    }


async def _run(input_dir: Path) -> dict[str, Any]:
    async with async_session() as session:
        report = await import_canonical_artifacts(session=session, input_dir=input_dir)
        await session.commit()
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate JSONL files and manifest counts without writing to the database.",
    )
    args = parser.parse_args()
    if args.validate_only:
        report = validate_canonical_artifacts(args.input_dir)
        report.pop("_loaded_rows", None)
    else:
        report = asyncio.run(_run(args.input_dir))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
