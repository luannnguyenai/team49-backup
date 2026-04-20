"""SQLAlchemy ORM models for Knowledge Graph storage tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base

_NODE_KIND = ("module", "topic", "kc", "concept", "question", "skill")
_EDGE_TYPE = (
    "INSTANCE_OF",
    "ALIGNS_WITH",
    "TRANSFERS_TO",
    "REQUIRES_KC",
    "DEVELOPS",
    "COVERS",
)
_EDGE_SOURCE = ("schema", "manual", "embedding", "llm", "heuristic")
_CONCEPT_SOURCE = ("manual", "embedding", "llm", "heuristic")


class KGConceptORM(Base):
    """ORM mapping for the kg_concepts table."""

    __tablename__ = "kg_concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_kc_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(
        Enum(*_CONCEPT_SOURCE, name="concept_source_enum", create_type=False),
        nullable=False,
    )
    embedding_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_kg_concepts_canonical_kc_slug", "canonical_kc_slug"),
        Index("ix_kg_concepts_is_deleted", "is_deleted"),
    )


class KGEdgeORM(Base):
    """ORM mapping for the kg_edges table."""

    __tablename__ = "kg_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    src_kind: Mapped[str] = mapped_column(
        Enum(*_NODE_KIND, name="node_kind_enum", create_type=False),
        nullable=False,
    )
    src_ref: Mapped[str] = mapped_column(Text, nullable=False)
    dst_kind: Mapped[str] = mapped_column(
        Enum(*_NODE_KIND, name="node_kind_enum", create_type=False),
        nullable=False,
    )
    dst_ref: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum(*_EDGE_TYPE, name="edge_type_enum", create_type=False),
        nullable=False,
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(
        Enum(*_EDGE_SOURCE, name="edge_source_enum", create_type=False),
        nullable=False,
    )
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "src_kind",
            "src_ref",
            "dst_kind",
            "dst_ref",
            "type",
            name="uq_kg_edges_src_dst_type",
        ),
        Index("ix_kg_edges_src", "src_kind", "src_ref"),
        Index("ix_kg_edges_dst", "dst_kind", "dst_ref"),
        Index("ix_kg_edges_type", "type"),
        Index("ix_kg_edges_is_deleted", "is_deleted"),
    )


class KGSyncStateORM(Base):
    """ORM mapping for the kg_sync_state table."""

    __tablename__ = "kg_sync_state"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_ref: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ok")

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_ref", name="uq_kg_sync_state_entity"),
        Index("ix_kg_sync_state_entity_type", "entity_type"),
        Index("ix_kg_sync_state_synced_at", "synced_at"),
    )
