from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def fail_if_any_errors(result: ValidationResult) -> int:
    return 1 if result.errors else 0


def write_validation_report(result: ValidationResult, path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "errors": result.errors,
                "warnings": result.warnings,
            },
            indent=2,
            sort_keys=True,
        )
    )


async def _scalar_int(session: AsyncSession, sql: str) -> int:
    value = (await session.execute(text(sql))).scalar_one()
    return int(value or 0)


async def validate_database() -> ValidationResult:
    result = ValidationResult()
    async with async_session() as session:
        unresolved_interactions = await _scalar_int(
            session,
            """
            SELECT COUNT(*)
            FROM interactions i
            LEFT JOIN question_bank q ON q.item_id = i.canonical_item_id
            WHERE i.canonical_item_id IS NOT NULL
              AND q.item_id IS NULL
            """,
        )
        if unresolved_interactions:
            result.error(
                f"{unresolved_interactions} interactions have unresolved canonical_item_id"
            )

        bad_item_weights = await _scalar_int(
            session,
            """
            SELECT COUNT(*)
            FROM (
              SELECT item_id, SUM(weight) AS total_weight
              FROM item_kp_map
              GROUP BY item_id
              HAVING ABS(COALESCE(SUM(weight), 0) - 1.0) > 0.001
            ) t
            """,
        )
        if bad_item_weights:
            result.error(f"{bad_item_weights} item_kp_map rowsets do not sum to 1.0")

        invalid_calibrated_items = await _scalar_int(
            session,
            """
            SELECT COUNT(*)
            FROM item_calibration
            WHERE is_calibrated = true
              AND (
                difficulty_b IS NULL
                OR discrimination_a IS NULL
                OR standard_error_b IS NULL
                OR irt_calibration_n IS NULL
              )
            """,
        )
        if invalid_calibrated_items:
            result.error(f"{invalid_calibrated_items} calibrated items are missing fitted params")

        unresolved_edges = await _scalar_int(
            session,
            """
            SELECT COUNT(*)
            FROM prerequisite_edges pe
            LEFT JOIN concepts_kp s ON s.kp_id = pe.source_kp_id
            LEFT JOIN concepts_kp t ON t.kp_id = pe.target_kp_id
            WHERE COALESCE(pe.active, true) = true
              AND (s.kp_id IS NULL OR t.kp_id IS NULL)
            """,
        )
        if unresolved_edges:
            result.error(f"{unresolved_edges} active prerequisite edges have unresolved KP IDs")

        null_content_type = await _scalar_int(
            session, "SELECT COUNT(*) FROM units WHERE content_type IS NULL"
        )
        if null_content_type:
            result.warning(
                f"{null_content_type} units have null content_type; expected until semantic ingest updates"
            )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Schema v2 database invariants.")
    parser.add_argument("--report-path", default="reports/schema_v2_validation_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = asyncio.run(validate_database())
    write_validation_report(result, args.report_path)
    print(
        json.dumps({"errors": result.errors, "warnings": result.warnings}, indent=2, sort_keys=True)
    )
    return fail_if_any_errors(result)


if __name__ == "__main__":
    raise SystemExit(main())
