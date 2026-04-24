"""Archive-only helper retained for audit before/after legacy table cleanup.

Do not use this script as a runtime data source. The active production contract
is canonical content plus product shell tables.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session
from src.scripts.pipeline.validate_legacy_cleanup_targets import (
    LEGACY_CLEANUP_ALLOWLIST,
    validate_cleanup_targets,
)

LEGACY_RUNTIME_TABLES: tuple[str, ...] = tuple(sorted(LEGACY_CLEANUP_ALLOWLIST))

DEFAULT_OUTPUT_ROOT = Path("data/legacy_archive")


def timestamped_output_dir(root: Path, now: datetime | None = None) -> Path:
    value = now or datetime.now(UTC)
    return root / value.strftime("%Y%m%dT%H%M%SZ")


def _json_default(value: Any) -> str:
    return str(value)


def encode_json_line(row: dict[str, Any]) -> str:
    return json.dumps(row, default=_json_default, ensure_ascii=False, sort_keys=True)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            line = encode_json_line(row)
            encoded = f"{line}\n".encode("utf-8")
            digest.update(encoded)
            handle.write(line)
            handle.write("\n")
    return {
        "rows": len(rows),
        "sha256": digest.hexdigest(),
        "path": str(path),
    }


def build_manifest(*, output_dir: Path, table_exports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir),
        "tables": table_exports,
    }


async def fetch_table_rows(session: AsyncSession, table_name: str) -> list[dict[str, Any]]:
    if table_name not in LEGACY_RUNTIME_TABLES:
        raise ValueError(f"Unsupported legacy table: {table_name}")
    result = await session.execute(text(f'SELECT * FROM "{table_name}" ORDER BY id'))
    return [dict(row) for row in result.mappings().all()]


async def export_legacy_runtime_data(
    session: AsyncSession,
    output_dir: Path,
    *,
    tables: tuple[str, ...] = LEGACY_RUNTIME_TABLES,
) -> dict[str, Any]:
    target_report = validate_cleanup_targets(list(tables))
    if target_report["status"] != "ready":
        raise ValueError(f"Unsafe legacy export targets: {target_report}")

    output_dir.mkdir(parents=True, exist_ok=True)
    table_exports: dict[str, dict[str, Any]] = {}
    for table_name in tables:
        rows = await fetch_table_rows(session, table_name)
        table_exports[table_name] = write_jsonl(output_dir / f"{table_name}.jsonl", rows)

    manifest = build_manifest(output_dir=output_dir, table_exports=table_exports)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


async def _run(output_dir: Path, tables: tuple[str, ...]) -> dict[str, Any]:
    async with async_session() as session:
        return await export_legacy_runtime_data(session, output_dir, tables=tables)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export legacy runtime tables to JSONL archive files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Archive output directory. Defaults to data/legacy_archive/<timestamp>.",
    )
    parser.add_argument(
        "--table",
        action="append",
        choices=LEGACY_RUNTIME_TABLES,
        help="Specific legacy table to export. Repeat to export multiple tables.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or timestamped_output_dir(DEFAULT_OUTPUT_ROOT)
    tables = tuple(args.table) if args.table else LEGACY_RUNTIME_TABLES
    manifest = asyncio.run(_run(output_dir, tables))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
