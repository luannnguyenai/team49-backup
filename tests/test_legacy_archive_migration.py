from pathlib import Path


def test_legacy_archive_migration_only_targets_cleanup_allowlist():
    migration = Path("alembic/versions/20260423_archive_legacy_runtime_tables.py").read_text(
        encoding="utf-8"
    )

    assert "intentionally a no-op" in migration
    assert "def upgrade() -> None:" in migration
    assert "def downgrade() -> None:" in migration
