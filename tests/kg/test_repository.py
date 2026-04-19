"""Integration tests for KGRepository sync behavior."""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.kg.models import KGConceptORM, KGEdgeORM, KGSyncStateORM
from src.kg.repository import KGRepository, edge_entity_ref
from src.kg.schemas import KGConcept, KGEdge
from src.models.base import Base


pytestmark = pytest.mark.asyncio


async def _ensure_kg_tables(db_session: AsyncSession) -> None:
    """Create KG tables in test DBs that have not run Alembic yet."""
    bind = await db_session.connection()
    await bind.run_sync(KGSyncStateORM.__table__.drop, checkfirst=True)
    await bind.run_sync(KGEdgeORM.__table__.drop, checkfirst=True)
    await bind.run_sync(KGConceptORM.__table__.drop, checkfirst=True)
    await bind.run_sync(Base.metadata.create_all, tables=[
        KGConceptORM.__table__,
        KGEdgeORM.__table__,
        KGSyncStateORM.__table__,
    ])


@pytest.fixture
def concept() -> KGConcept:
    """Return one stable concept payload."""
    return KGConcept(
        id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
        name="Self-Attention",
        description="Q/K/V attention",
        canonical_kc_slug="KC-NLP-self-attention",
        source="manual",
    )


@pytest.fixture
def manual_edge() -> KGEdge:
    """Return one manual INSTANCE_OF edge."""
    return KGEdge(
        src_kind="kc",
        src_ref="KC-NLP-self-attention",
        dst_kind="concept",
        dst_ref="CON-self-attention",
        type="INSTANCE_OF",
        weight=1.0,
        source="manual",
    )


@pytest.fixture
def schema_edge() -> KGEdge:
    """Return one schema-owned edge that may be auto-soft-deleted."""
    return KGEdge(
        src_kind="topic",
        src_ref="topic-a",
        dst_kind="topic",
        dst_ref="topic-b",
        type="TRANSFERS_TO",
        weight=0.8,
        source="schema",
    )


async def test_sync_first_run_marks_all_created(
    db_session: AsyncSession,
    concept: KGConcept,
    manual_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    report = await KGRepository(db_session).sync([concept], [manual_edge])

    assert report.created == (f"concept:{concept.id}", f"edge:{edge_entity_ref(manual_edge)}")
    assert report.updated == ()
    assert report.unchanged == ()
    assert report.soft_deleted == ()


async def test_sync_second_run_marks_all_unchanged(
    db_session: AsyncSession,
    concept: KGConcept,
    manual_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    repo = KGRepository(db_session)

    await repo.sync([concept], [manual_edge])
    report = await repo.sync([concept], [manual_edge])

    assert report.created == ()
    assert report.updated == ()
    assert report.unchanged == (f"concept:{concept.id}", f"edge:{edge_entity_ref(manual_edge)}")
    assert report.soft_deleted == ()


async def test_sync_changed_concept_marks_updated(
    db_session: AsyncSession,
    concept: KGConcept,
    manual_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    repo = KGRepository(db_session)
    changed = concept.model_copy(update={"name": "Self-Attention Updated"})

    await repo.sync([concept], [manual_edge])
    report = await repo.sync([changed], [manual_edge])

    assert report.created == ()
    assert report.updated == (f"concept:{concept.id}",)
    assert f"edge:{edge_entity_ref(manual_edge)}" in report.unchanged


async def test_sync_does_not_auto_soft_delete_missing_manual_edge(
    db_session: AsyncSession,
    concept: KGConcept,
    manual_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    repo = KGRepository(db_session)

    await repo.sync([concept], [manual_edge])
    report = await repo.sync([concept], [])
    edge_row = (
        await db_session.execute(
            sa.select(KGEdgeORM).where(KGEdgeORM.src_ref == manual_edge.src_ref)
        )
    ).scalar_one()

    assert report.soft_deleted == ()
    assert edge_row.deleted_at is None
    assert edge_row.is_deleted is False


async def test_sync_soft_deletes_missing_schema_edge(
    db_session: AsyncSession,
    concept: KGConcept,
    schema_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    repo = KGRepository(db_session)

    await repo.sync([concept], [schema_edge])
    report = await repo.sync([concept], [])
    edge_row = (
        await db_session.execute(
            sa.select(KGEdgeORM).where(KGEdgeORM.src_ref == schema_edge.src_ref)
        )
    ).scalar_one()

    assert report.soft_deleted == (f"edge:{edge_entity_ref(schema_edge)}",)
    assert edge_row.deleted_at is not None
    assert edge_row.is_deleted is True


async def test_sync_undeletes_previously_soft_deleted_edge(
    db_session: AsyncSession,
    concept: KGConcept,
    schema_edge: KGEdge,
) -> None:
    await _ensure_kg_tables(db_session)
    repo = KGRepository(db_session)

    await repo.sync([concept], [schema_edge])
    await repo.sync([concept], [])
    report = await repo.sync([concept], [schema_edge])
    edge_row = (
        await db_session.execute(
            sa.select(KGEdgeORM).where(KGEdgeORM.src_ref == schema_edge.src_ref)
        )
    ).scalar_one()

    assert f"edge:{edge_entity_ref(schema_edge)}" in report.unchanged
    assert edge_row.deleted_at is None
    assert edge_row.is_deleted is False
