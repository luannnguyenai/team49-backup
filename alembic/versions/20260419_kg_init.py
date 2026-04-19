"""Create Knowledge Graph tables: kg_concepts, kg_edges, kg_sync_state.

Revision ID: 20260419_kg_init
Revises: 20260419_merge_final
Create Date: 2026-04-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import UserDefinedType

revision: str = "20260419_kg_init"
down_revision: str = "20260419_merge_final"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NODE_KIND = ("module", "topic", "kc", "concept", "question", "skill")
_EDGE_TYPE = (
    "INSTANCE_OF", "ALIGNS_WITH", "TRANSFERS_TO",
    "REQUIRES_KC", "DEVELOPS", "COVERS",
)
_EDGE_SOURCE = ("schema", "manual", "embedding", "llm", "heuristic")
_CONCEPT_SOURCE = ("manual", "embedding", "llm", "heuristic")


class _Vector(UserDefinedType):
    """Inline vector type wrapper for pgvector — migration use only.

    Args:
        dim: Embedding dimensionality (e.g. 1536 for text-embedding-ada-002).
    """

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: object) -> str:
        """Return the PostgreSQL column type string."""
        return f"vector({self.dim})"


def upgrade() -> None:
    """Create kg_concepts, kg_edges, kg_sync_state with all indexes and constraints."""
    # Create enum types via raw SQL DO blocks (idempotent: no error on repeated runs)
    op.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'node_kind_enum') THEN "
        "    CREATE TYPE node_kind_enum AS ENUM "
        "      ('module', 'topic', 'kc', 'concept', 'question', 'skill'); "
        "  END IF; "
        "END $$;"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'edge_type_enum') THEN "
        "    CREATE TYPE edge_type_enum AS ENUM "
        "      ('INSTANCE_OF', 'ALIGNS_WITH', 'TRANSFERS_TO', "
        "       'REQUIRES_KC', 'DEVELOPS', 'COVERS'); "
        "  END IF; "
        "END $$;"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'edge_source_enum') THEN "
        "    CREATE TYPE edge_source_enum AS ENUM "
        "      ('schema', 'manual', 'embedding', 'llm', 'heuristic'); "
        "  END IF; "
        "END $$;"
    ))
    op.execute(sa.text(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'concept_source_enum') THEN "
        "    CREATE TYPE concept_source_enum AS ENUM "
        "      ('manual', 'embedding', 'llm', 'heuristic'); "
        "  END IF; "
        "END $$;"
    ))

    # ------------------------------------------------------------------ kg_concepts
    op.create_table(
        "kg_concepts",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("canonical_kc_slug", sa.String(100), nullable=True),
        sa.Column(
            "source",
            PG_ENUM(*_CONCEPT_SOURCE, name="concept_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("embedding_version", sa.Integer(), nullable=True),
        sa.Column("embedding", _Vector(1536), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        # TODO(phase-1): add BEFORE UPDATE trigger to auto-refresh updated_at
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_kg_concepts_canonical_kc_slug", "kg_concepts", ["canonical_kc_slug"])
    op.create_index("ix_kg_concepts_is_deleted", "kg_concepts", ["is_deleted"])

    # ------------------------------------------------------------------ kg_edges
    op.create_table(
        "kg_edges",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "src_kind",
            PG_ENUM(*_NODE_KIND, name="node_kind_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("src_ref", sa.Text(), nullable=False),
        sa.Column(
            "dst_kind",
            PG_ENUM(*_NODE_KIND, name="node_kind_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("dst_ref", sa.Text(), nullable=False),
        sa.Column(
            "type",
            PG_ENUM(*_EDGE_TYPE, name="edge_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column(
            "source",
            PG_ENUM(*_EDGE_SOURCE, name="edge_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("meta", JSONB(), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "src_kind", "src_ref", "dst_kind", "dst_ref", "type",
            name="uq_kg_edges_src_dst_type",
        ),
        sa.CheckConstraint("weight >= 0.0 AND weight <= 1.0", name="ck_kg_edges_weight"),
    )
    op.create_index("ix_kg_edges_src", "kg_edges", ["src_kind", "src_ref"])
    op.create_index("ix_kg_edges_dst", "kg_edges", ["dst_kind", "dst_ref"])
    op.create_index("ix_kg_edges_type", "kg_edges", ["type"])
    op.create_index("ix_kg_edges_is_deleted", "kg_edges", ["is_deleted"])

    # ------------------------------------------------------------------ kg_sync_state
    op.create_table(
        "kg_sync_state",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_ref", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "synced_at", sa.TIMESTAMP(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ok'")),
        sa.UniqueConstraint("entity_type", "entity_ref", name="uq_kg_sync_state_entity"),
    )
    op.create_index("ix_kg_sync_state_entity_type", "kg_sync_state", ["entity_type"])
    op.create_index("ix_kg_sync_state_synced_at", "kg_sync_state", ["synced_at"])


def downgrade() -> None:
    """Drop all KG tables and enum types in reverse order."""
    op.drop_table("kg_sync_state")
    op.drop_table("kg_edges")
    op.drop_table("kg_concepts")

    op.execute(sa.text("DROP TYPE IF EXISTS concept_source_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS edge_source_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS edge_type_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS node_kind_enum"))
