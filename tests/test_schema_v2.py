import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.scripts.schema_v2.apply_reviewed_unit_labels import apply_labels
from src.scripts.schema_v2.backfill_schema_v2 import (
    BackfillReport,
    _backfill_calibration_and_interactions,
    build_default_course_config,
    derive_salience_decision,
    sha256_json,
    write_report,
)
from src.scripts.schema_v2.sync_schema_v2 import build_sync_commands
from src.scripts.schema_v2.validate_schema_v2 import ValidationResult, fail_if_any_errors


MIGRATION = Path("alembic/versions/20260427_schema_v2_additive_audit.py")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _upgrade_body(text: str) -> str:
    return text.split("def upgrade() -> None:", 1)[1].split("def downgrade() -> None:", 1)[0]


def test_schema_v2_migration_is_additive_and_declares_audit_tables() -> None:
    assert MIGRATION.exists()
    text = MIGRATION.read_text()
    assert 'down_revision: str | None = "20260424_resume_state"' in text
    assert "op.add_column" in text
    assert "op.create_table" in text

    upgrade_body = _upgrade_body(text)
    assert "op.drop_table" not in upgrade_body
    assert "op.drop_column" not in upgrade_body

    for table_name in [
        "ingest_runs",
        "kp_migration",
        "calibration_runs",
        "item_calibration_history",
        "item_exposure_stats",
        "human_review_queue",
    ]:
        assert f'"{table_name}"' in text


def test_schema_v2_backfill_helpers_are_stable_and_conservative(tmp_path: Path) -> None:
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})

    config = build_default_course_config()
    assert config["included_content_types"] == ["core_theory", "worked_example", "application_case"]
    assert config["salience_filter_strictness"] == "normal"
    assert config["default_question_item_types"] == ["MCQ"]
    assert config["allow_free_response"] is False

    assert derive_salience_decision(has_quiz_items=True, override_critical_kp=False) == {
        "is_worth_learning": True,
        "salience_score": "medium",
        "salience_decision": "core",
    }
    assert derive_salience_decision(has_quiz_items=False, override_critical_kp=True) == {
        "is_worth_learning": True,
        "salience_score": "medium",
        "salience_decision": "core",
    }
    assert derive_salience_decision(has_quiz_items=False, override_critical_kp=False) == {
        "is_worth_learning": None,
        "salience_score": None,
        "salience_decision": None,
    }

    report_path = tmp_path / "report.json"
    report = BackfillReport(dry_run=True)
    report.inc("courses.course_config")
    write_report(report, str(report_path))
    assert '"courses.course_config": 1' in report_path.read_text()


def test_schema_v2_label_application_updates_only_unit_runtime_fields(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "units.jsonl",
        [
            {
                "unit_id": "u1",
                "course_id": "CSX",
                "lecture_id": "L1",
                "unit_name": "Unit 1",
                "summary": "Summary",
                "content_ref": {"start_s": 0, "end_s": 60},
                "key_points": [],
                "transcript_path": "transcript.txt",
                "video_clip_ref": None,
            }
        ],
    )
    labels_path = tmp_path / "labels.jsonl"
    _write_jsonl(
        labels_path,
        [
            {
                "unit_id": "u1",
                "content_type": "core_theory",
                "content_type_confidence": "high",
                "is_worth_learning": True,
                "salience_score": "high",
                "salience_confidence": "high",
                "has_quiz_items": True,
                "override_critical_kp": False,
                "active": True,
                "review_rationale": "not copied into units",
            }
        ],
    )

    report = apply_labels(tmp_path, labels_path)
    row = _read_jsonl(tmp_path / "units.jsonl")[0]

    assert report["applied_count"] == 1
    assert row["content_type"] == "core_theory"
    assert row["salience_score"] == "high"
    assert row["has_quiz_items"] is True
    assert row["content_hash"]
    assert "review_rationale" not in row


def test_schema_v2_sync_command_order() -> None:
    commands = build_sync_commands(import_bundle=None)
    assert commands == [
        ["alembic", "upgrade", "head"],
        [
            "python",
            "-m",
            "src.scripts.schema_v2.backfill_schema_v2",
            "--apply",
            "--report-path",
            "reports/schema_v2_backfill_report.json",
        ],
        [
            "python",
            "-m",
            "src.scripts.schema_v2.validate_schema_v2",
            "--report-path",
            "reports/schema_v2_validation_report.json",
        ],
        ["python", "-m", "src.scripts.pipeline.check_canonical_runtime_parity"],
    ]

    commands = build_sync_commands(import_bundle="data/final_artifacts/cs224n_cs231n_cs230_v1/canonical")
    assert commands[0] == ["alembic", "upgrade", "head"]
    assert commands[1] == [
        "python",
        "-m",
        "src.scripts.pipeline.import_canonical_artifacts_to_db",
        "--input-dir",
        "data/final_artifacts/cs224n_cs231n_cs230_v1/canonical",
    ]
    assert commands[2][2] == "src.scripts.schema_v2.backfill_schema_v2"


def test_schema_v2_validation_result_exit_codes() -> None:
    result = ValidationResult()
    result.error("bad")
    result.warning("soft")
    assert result.errors == ["bad"]
    assert result.warnings == ["soft"]
    assert fail_if_any_errors(result) == 1
    assert fail_if_any_errors(ValidationResult(errors=[], warnings=["soft"])) == 0


async def test_schema_v2_backfill_uses_column_names_for_interaction_null_counts() -> None:
    session = SimpleNamespace()
    session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: 0))
    report = BackfillReport(dry_run=True)

    await _backfill_calibration_and_interactions(session, report)

    executed_sql = [
        call.args[0].text if hasattr(call.args[0], "text") else str(call.args[0])
        for call in session.execute.await_args_list
    ]

    assert any("interactions WHERE theta_before IS NULL" in sql for sql in executed_sql)
    assert any("interactions WHERE theta_after IS NULL" in sql for sql in executed_sql)
    assert not any("<function field" in sql for sql in executed_sql)
