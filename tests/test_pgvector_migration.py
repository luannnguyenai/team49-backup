from pathlib import Path


def test_pgvector_extension_migration_exists_and_targets_current_head():
    migration = Path("alembic/versions/20260418_enable_pgvector_extension.py")

    assert migration.exists()

    content = migration.read_text()
    assert 'revision: str = "20260418_enable_pgvector_extension"' in content
    assert 'down_revision: str | None = "20260418_merge_heads"' in content
    assert 'CREATE EXTENSION IF NOT EXISTS vector;' in content
