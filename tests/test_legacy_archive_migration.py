from pathlib import Path


def test_legacy_archive_migration_only_targets_cleanup_allowlist():
    migration = Path("alembic/versions/20260423_archive_legacy_runtime_tables.py").read_text(
        encoding="utf-8"
    )

    for table_name in (
        "questions",
        "mastery_scores",
        "mastery_history",
        "learning_paths",
        "modules",
        "topics",
        "knowledge_components",
    ):
        assert f'"{table_name}"' in migration
        assert f'"{table_name}_legacy_archived"' in migration

    for protected_table in (
        "question_bank",
        "learner_mastery_kp",
        "goal_preferences",
        "plan_history",
        "rationale_log",
        "planner_session_state",
        "learning_units",
        "interactions",
        "sessions",
        "users",
    ):
        assert f'"{protected_table}"' not in migration
        assert f'"{protected_table}_legacy_archived"' not in migration
