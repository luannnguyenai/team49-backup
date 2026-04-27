from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session

DEFAULT_RUN_ID = "schema_v2_backfill_20260427"


@dataclass
class BackfillReport:
    run_id: str = DEFAULT_RUN_ID
    dry_run: bool = True
    updated_counts: dict[str, int] = field(default_factory=dict)
    null_counts: dict[str, int] = field(default_factory=dict)
    hitl_candidates: list[dict[str, Any]] = field(default_factory=list)

    def inc(self, key: str, amount: int = 1) -> None:
        self.updated_counts[key] = self.updated_counts.get(key, 0) + amount

    def note_null(self, key: str, amount: int) -> None:
        self.null_counts[key] = self.null_counts.get(key, 0) + amount


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_default_course_config() -> dict[str, Any]:
    return {
        "included_content_types": ["core_theory", "worked_example", "application_case"],
        "salience_filter_strictness": "normal",
        "default_question_item_types": ["MCQ"],
        "allow_free_response": False,
    }


def derive_salience_decision(*, has_quiz_items: bool, override_critical_kp: bool) -> dict[str, str | bool | None]:
    if has_quiz_items or override_critical_kp:
        return {
            "is_worth_learning": True,
            "salience_score": "medium",
            "salience_decision": "core",
        }
    return {
        "is_worth_learning": None,
        "salience_score": None,
        "salience_decision": None,
    }


def write_report(report: BackfillReport, path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "run_id": report.run_id,
                "dry_run": report.dry_run,
                "updated_counts": report.updated_counts,
                "null_counts": report.null_counts,
                "hitl_candidates": report.hitl_candidates,
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )


async def _scalar_int(session: AsyncSession, sql: str, params: dict[str, Any] | None = None) -> int:
    result = await session.execute(text(sql), params or {})
    value = result.scalar_one()
    return int(value or 0)


async def _execute_counted(
    session: AsyncSession,
    report: BackfillReport,
    key: str,
    count_sql: str,
    update_sql: str,
    params: dict[str, Any] | None = None,
) -> None:
    count = await _scalar_int(session, count_sql, params)
    report.inc(key, count)
    if count and not report.dry_run:
        await session.execute(text(update_sql), params or {})


async def _backfill_courses(session: AsyncSession, report: BackfillReport) -> None:
    default_config = build_default_course_config()
    await _execute_counted(
        session,
        report,
        "courses.course_config",
        "SELECT COUNT(*) FROM courses WHERE course_config IS NULL",
        "UPDATE courses SET course_config = :default_config WHERE course_config IS NULL",
        {"default_config": json.dumps(default_config)},
    )


async def _backfill_hashes(session: AsyncSession, report: BackfillReport) -> None:
    unit_rows = (
        await session.execute(
            text(
                """
                SELECT unit_id, course_id, lecture_id, unit_name, summary, content_ref,
                       key_points, transcript_path, video_clip_ref
                FROM units
                WHERE content_hash IS NULL
                """
            )
        )
    ).mappings()
    unit_updates = []
    for row in unit_rows:
        digest = sha256_json(dict(row))
        unit_updates.append({"unit_id": row["unit_id"], "content_hash": digest})
    report.inc("units.content_hash", len(unit_updates))
    if unit_updates and not report.dry_run:
        await session.execute(
            text("UPDATE units SET content_hash = :content_hash WHERE unit_id = :unit_id"),
            unit_updates,
        )

    concept_rows = (
        await session.execute(
            text(
                """
                SELECT kp_id, name, description, track_tags, domain_tags, career_path_tags,
                       difficulty_level, importance_level, structural_role, importance_scope
                FROM concepts_kp
                WHERE content_hash IS NULL
                """
            )
        )
    ).mappings()
    concept_updates = []
    for row in concept_rows:
        digest = sha256_json(dict(row))
        concept_updates.append({"kp_id": row["kp_id"], "content_hash": digest})
    report.inc("concepts_kp.content_hash", len(concept_updates))
    if concept_updates and not report.dry_run:
        await session.execute(
            text("UPDATE concepts_kp SET content_hash = :content_hash WHERE kp_id = :kp_id"),
            concept_updates,
        )


async def _backfill_unit_salience(session: AsyncSession, report: BackfillReport) -> None:
    await _execute_counted(
        session,
        report,
        "units.has_quiz_items",
        """
        SELECT COUNT(*)
        FROM units u
        WHERE COALESCE(u.has_quiz_items, false) = false
          AND EXISTS (
            SELECT 1 FROM question_bank q
            WHERE q.unit_id = u.unit_id
              AND COALESCE(q.qa_gate_passed, true) = true
          )
        """,
        """
        WITH quiz_units AS (
          SELECT unit_id
          FROM question_bank
          WHERE COALESCE(qa_gate_passed, true) = true
          GROUP BY unit_id
        )
        UPDATE units u
        SET has_quiz_items = true
        FROM quiz_units q
        WHERE u.unit_id = q.unit_id
        """,
    )
    await _execute_counted(
        session,
        report,
        "units.override_critical_kp",
        """
        SELECT COUNT(*)
        FROM units u
        WHERE COALESCE(u.override_critical_kp, false) = false
          AND EXISTS (
            SELECT 1
            FROM unit_kp_map ukm
            JOIN concepts_kp c ON c.kp_id = ukm.kp_id
            WHERE ukm.unit_id = u.unit_id
              AND c.importance_level = 'critical'
              AND c.structural_role = 'gateway'
          )
        """,
        """
        WITH critical_units AS (
          SELECT DISTINCT ukm.unit_id
          FROM unit_kp_map ukm
          JOIN concepts_kp c ON c.kp_id = ukm.kp_id
          WHERE c.importance_level = 'critical'
            AND c.structural_role = 'gateway'
        )
        UPDATE units u
        SET override_critical_kp = true
        FROM critical_units cu
        WHERE u.unit_id = cu.unit_id
        """,
    )
    await _execute_counted(
        session,
        report,
        "units.salience",
        """
        SELECT COUNT(*)
        FROM units
        WHERE (has_quiz_items = true OR override_critical_kp = true)
          AND is_worth_learning IS DISTINCT FROM true
        """,
        """
        UPDATE units
        SET is_worth_learning = true,
            salience_score = 'medium',
            salience_confidence = 'low'
        WHERE has_quiz_items = true OR override_critical_kp = true
        """,
    )
    null_content_type = await _scalar_int(session, "SELECT COUNT(*) FROM units WHERE content_type IS NULL")
    report.note_null("units.content_type", null_content_type)


async def _backfill_learning_units(session: AsyncSession, report: BackfillReport) -> None:
    await _execute_counted(
        session,
        report,
        "learning_units.schema_v2_cache",
        """
        SELECT COUNT(*)
        FROM learning_units lu
        JOIN units u ON lu.canonical_unit_id = u.unit_id
        WHERE lu.has_quiz_items IS DISTINCT FROM u.has_quiz_items
           OR lu.salience_decision IS DISTINCT FROM CASE
                WHEN u.is_worth_learning = true AND u.salience_score IN ('medium', 'high') THEN 'core'
                WHEN u.is_worth_learning = true AND u.salience_score = 'low' THEN 'reference'
                WHEN u.is_worth_learning = false OR u.salience_score = 'skip' THEN 'skip'
                ELSE NULL
              END
        """,
        """
        UPDATE learning_units lu
        SET has_quiz_items = u.has_quiz_items,
            salience_decision = CASE
              WHEN u.is_worth_learning = true AND u.salience_score IN ('medium', 'high') THEN 'core'
              WHEN u.is_worth_learning = true AND u.salience_score = 'low' THEN 'reference'
              WHEN u.is_worth_learning = false OR u.salience_score = 'skip' THEN 'skip'
              ELSE NULL
            END
        FROM units u
        WHERE lu.canonical_unit_id = u.unit_id
        """,
    )


async def _backfill_calibration_and_interactions(session: AsyncSession, report: BackfillReport) -> None:
    await _execute_counted(
        session,
        report,
        "item_calibration.real_response_count",
        """
        SELECT COUNT(*)
        FROM item_calibration ic
        WHERE ic.real_response_count IS DISTINCT FROM (
          SELECT COUNT(*)::int
          FROM interactions i
          WHERE i.canonical_item_id = ic.item_id
        )
        """,
        """
        WITH response_counts AS (
          SELECT canonical_item_id AS item_id, COUNT(*)::int AS real_response_count
          FROM interactions
          WHERE canonical_item_id IS NOT NULL
          GROUP BY canonical_item_id
        )
        UPDATE item_calibration ic
        SET real_response_count = COALESCE(rc.real_response_count, 0),
            synthetic_response_count = 0
        FROM response_counts rc
        WHERE ic.item_id = rc.item_id
        """,
    )
    await _execute_counted(
        session,
        report,
        "interactions.item_parameter_snapshots",
        """
        SELECT COUNT(*)
        FROM interactions i
        JOIN item_calibration ic ON ic.item_id = i.canonical_item_id
        WHERE i.item_difficulty_at_time IS DISTINCT FROM ic.difficulty_prior
           OR i.item_discrimination_at_time IS DISTINCT FROM ic.discrimination_prior
           OR i.item_guessing_at_time IS DISTINCT FROM ic.guessing_prior
           OR i.selection_strategy IS NULL
        """,
        """
        UPDATE interactions i
        SET item_difficulty_at_time = ic.difficulty_prior,
            item_discrimination_at_time = ic.discrimination_prior,
            item_guessing_at_time = ic.guessing_prior,
            selection_strategy = COALESCE(i.selection_strategy, 'unknown_legacy')
        FROM item_calibration ic
        WHERE i.canonical_item_id = ic.item_id
        """,
    )
    for field in [
        "theta_before",
        "theta_after",
        "theta_sigma_before",
        "theta_sigma_after",
        "predicted_probability",
        "item_information",
    ]:
        report.note_null(
            f"interactions.{field}",
            await _scalar_int(session, f"SELECT COUNT(*) FROM interactions WHERE {field} IS NULL"),
        )


async def _backfill_item_kp_weights(session: AsyncSession, report: BackfillReport) -> None:
    bad_items = await _scalar_int(
        session,
        """
        SELECT COUNT(*)
        FROM (
          SELECT item_id, SUM(weight) AS total_weight
          FROM item_kp_map
          GROUP BY item_id
          HAVING SUM(weight) IS NOT NULL
             AND SUM(weight) > 0
             AND ABS(SUM(weight) - 1.0) > 0.001
        ) t
        """,
    )
    report.inc("item_kp_map.normalized_weights", bad_items)
    if bad_items and not report.dry_run:
        await session.execute(
            text(
                """
                WITH totals AS (
                  SELECT item_id, SUM(weight) AS total_weight
                  FROM item_kp_map
                  GROUP BY item_id
                  HAVING SUM(weight) IS NOT NULL
                     AND SUM(weight) > 0
                     AND ABS(SUM(weight) - 1.0) > 0.001
                )
                UPDATE item_kp_map ikm
                SET weight = ikm.weight / totals.total_weight
                FROM totals
                WHERE ikm.item_id = totals.item_id
                  AND ikm.weight IS NOT NULL
                """
            )
        )
    zero_or_null_items = await _scalar_int(
        session,
        """
        SELECT COUNT(*)
        FROM (
          SELECT item_id, SUM(weight) AS total_weight
          FROM item_kp_map
          GROUP BY item_id
          HAVING SUM(weight) IS NULL OR SUM(weight) <= 0
        ) t
        """,
    )
    if zero_or_null_items:
        report.hitl_candidates.append(
            {
                "entity_type": "item_kp_map",
                "reason": "weight_sum_missing_or_zero",
                "count": zero_or_null_items,
                "suggested_action": "Review item KP mappings; deterministic normalization is impossible.",
            }
        )


async def _backfill_item_exposure(session: AsyncSession, report: BackfillReport) -> None:
    count = await _scalar_int(
        session,
        """
        SELECT COUNT(*)
        FROM (
          SELECT i.canonical_item_id, COALESCE(s.canonical_phase, 'unknown_legacy') AS phase
          FROM interactions i
          JOIN sessions s ON s.id = i.session_id
          WHERE i.canonical_item_id IS NOT NULL
          GROUP BY i.canonical_item_id, COALESCE(s.canonical_phase, 'unknown_legacy')
        ) t
        """,
    )
    report.inc("item_exposure_stats", count)
    if count and not report.dry_run:
        await session.execute(
            text(
                """
                INSERT INTO item_exposure_stats (
                  item_id,
                  phase,
                  shown_count,
                  answered_count,
                  correct_count,
                  last_shown_at,
                  refreshed_at
                )
                SELECT
                  i.canonical_item_id,
                  COALESCE(s.canonical_phase, 'unknown_legacy') AS phase,
                  COUNT(*)::int AS shown_count,
                  COUNT(*)::int AS answered_count,
                  SUM(CASE WHEN i.is_correct THEN 1 ELSE 0 END)::int AS correct_count,
                  MAX(i.timestamp) AS last_shown_at,
                  now() AS refreshed_at
                FROM interactions i
                JOIN sessions s ON s.id = i.session_id
                WHERE i.canonical_item_id IS NOT NULL
                GROUP BY i.canonical_item_id, COALESCE(s.canonical_phase, 'unknown_legacy')
                ON CONFLICT (item_id, phase) DO UPDATE
                SET shown_count = EXCLUDED.shown_count,
                    answered_count = EXCLUDED.answered_count,
                    correct_count = EXCLUDED.correct_count,
                    last_shown_at = EXCLUDED.last_shown_at,
                    refreshed_at = EXCLUDED.refreshed_at
                """
            )
        )


async def _backfill_edges(session: AsyncSession, report: BackfillReport) -> None:
    await _execute_counted(
        session,
        report,
        "prerequisite_edges.schema_v2",
        """
        SELECT COUNT(*)
        FROM prerequisite_edges
        WHERE edge_kind IS NULL OR evidence_ledger IS NULL OR active IS DISTINCT FROM true
        """,
        """
        UPDATE prerequisite_edges
        SET active = true,
            edge_kind = COALESCE(edge_kind, 'hard'),
            evidence_ledger = COALESCE(
              evidence_ledger,
              jsonb_build_array(jsonb_build_object(
                'source', 'legacy_graph_import',
                'added_in_run', 'schema_v2_backfill_20260427',
                'confidence', COALESCE(confidence, 'unknown')
              ))
            )
        """,
    )
    await _execute_counted(
        session,
        report,
        "pruned_edges.schema_v2",
        """
        SELECT COUNT(*)
        FROM pruned_edges
        WHERE active IS DISTINCT FROM false OR adjudication_trace IS NULL
        """,
        """
        UPDATE pruned_edges
        SET active = false,
            adjudication_trace = COALESCE(
              adjudication_trace,
              jsonb_build_object(
                'source', 'legacy_pruned_edge_import',
                'added_in_run', 'schema_v2_backfill_20260427'
              )
            )
        """,
    )


async def _record_ingest_run(session: AsyncSession, report: BackfillReport) -> None:
    if report.dry_run:
        report.inc("ingest_runs.schema_backfill", 1)
        return
    await session.execute(
        text(
            """
            INSERT INTO ingest_runs (
              run_id,
              run_type,
              status,
              metrics_json,
              started_at,
              finished_at
            )
            VALUES (
              :run_id,
              'schema_backfill',
              'passed',
              CAST(:metrics_json AS jsonb),
              now(),
              now()
            )
            ON CONFLICT (run_id) DO UPDATE
            SET status = EXCLUDED.status,
                metrics_json = EXCLUDED.metrics_json,
                finished_at = EXCLUDED.finished_at,
                updated_at = now()
            """
        ),
        {
            "run_id": report.run_id,
            "metrics_json": json.dumps(
                {
                    "updated_counts": report.updated_counts,
                    "null_counts": report.null_counts,
                    "hitl_candidate_count": len(report.hitl_candidates),
                },
                sort_keys=True,
            ),
        },
    )
    report.inc("ingest_runs.schema_backfill", 1)


async def run_backfill(*, apply: bool) -> BackfillReport:
    report = BackfillReport(dry_run=not apply)
    async with async_session() as session:
        await _backfill_courses(session, report)
        await _backfill_hashes(session, report)
        await _backfill_unit_salience(session, report)
        await _backfill_learning_units(session, report)
        await _backfill_item_kp_weights(session, report)
        await _backfill_calibration_and_interactions(session, report)
        await _backfill_item_exposure(session, report)
        await _backfill_edges(session, report)
        await _record_ingest_run(session, report)
        if apply:
            await session.commit()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Schema v2 fields from existing DB data.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument("--report-path", default="reports/schema_v2_backfill_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = asyncio.run(run_backfill(apply=args.apply))
    write_report(report, args.report_path)
    print(json.dumps(report.__dict__, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
