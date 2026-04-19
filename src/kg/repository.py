"""Async repository for Knowledge Graph storage and sync."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import asynccontextmanager
from typing import Any

import sqlalchemy as sa
from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.kg.hashing import canonical_hash
from src.kg.models import KGConceptORM, KGEdgeORM, KGSyncStateORM
from src.kg.schemas import KGConcept, KGEdge, SyncReport

_AUTO_SOFT_DELETE_SOURCES = frozenset({"schema", "heuristic", "embedding", "llm"})


def edge_entity_ref(edge: KGEdge | KGEdgeORM) -> str:
    """Return the stable sync-state entity ref for an edge."""
    return f"{edge.src_kind}:{edge.src_ref}->{edge.dst_kind}:{edge.dst_ref}:{edge.type}"


def _concept_entity_ref(concept: KGConcept | KGConceptORM) -> str:
    """Return the stable sync-state entity ref for a concept."""
    return str(concept.id)


class KGRepository:
    """Async KG repository backed by a SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_concept(self, id: Any) -> KGConceptORM | None:
        """Fetch one non-deleted concept by UUID."""
        result = await self.session.execute(
            sa.select(KGConceptORM).where(
                KGConceptORM.id == id,
                KGConceptORM.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_concepts(self) -> list[KGConceptORM]:
        """List all non-deleted concepts."""
        result = await self.session.execute(
            sa.select(KGConceptORM)
            .where(KGConceptORM.deleted_at.is_(None))
            .order_by(KGConceptORM.name, KGConceptORM.id)
        )
        return list(result.scalars().all())

    async def list_edges(
        self,
        type: str | None = None,
        src_kind: str | None = None,
        src_ref: str | None = None,
    ) -> list[KGEdgeORM]:
        """List non-deleted edges filtered by optional type/source fields."""
        stmt = sa.select(KGEdgeORM).where(KGEdgeORM.deleted_at.is_(None))
        if type is not None:
            stmt = stmt.where(KGEdgeORM.type == type)
        if src_kind is not None:
            stmt = stmt.where(KGEdgeORM.src_kind == src_kind)
        if src_ref is not None:
            stmt = stmt.where(KGEdgeORM.src_ref == src_ref)
        result = await self.session.execute(
            stmt.order_by(KGEdgeORM.type, KGEdgeORM.src_kind, KGEdgeORM.src_ref)
        )
        return list(result.scalars().all())

    async def upsert_concept(self, concept: KGConcept) -> KGConceptORM:
        """Insert or update a KG concept by primary key."""
        values = {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description,
            "canonical_kc_slug": concept.canonical_kc_slug,
            "source": concept.source,
            "embedding_version": concept.embedding_version,
            "is_deleted": False,
            "deleted_at": None,
        }
        stmt = (
            pg_insert(KGConceptORM)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[KGConceptORM.id],
                set_={
                    "name": concept.name,
                    "description": concept.description,
                    "canonical_kc_slug": concept.canonical_kc_slug,
                    "source": concept.source,
                    "embedding_version": concept.embedding_version,
                    "is_deleted": False,
                    "deleted_at": None,
                    "updated_at": sa.func.now(),
                },
            )
            .returning(KGConceptORM)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def upsert_edge(self, edge: KGEdge) -> KGEdgeORM:
        """Insert or update a KG edge by its semantic unique key."""
        values = {
            "src_kind": edge.src_kind,
            "src_ref": edge.src_ref,
            "dst_kind": edge.dst_kind,
            "dst_ref": edge.dst_ref,
            "type": edge.type,
            "weight": edge.weight,
            "source": edge.source,
            "meta": edge.meta,
            "is_deleted": False,
            "deleted_at": None,
        }
        stmt = (
            pg_insert(KGEdgeORM)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_kg_edges_src_dst_type",
                set_={
                    "weight": edge.weight,
                    "source": edge.source,
                    "meta": edge.meta,
                    "is_deleted": False,
                    "deleted_at": None,
                    "updated_at": sa.func.now(),
                },
            )
            .returning(KGEdgeORM)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_sync_state(
        self,
        entity_id: str,
        kind: str | None = None,
    ) -> KGSyncStateORM | None:
        """Fetch one sync-state row by entity ref, optionally scoped by kind."""
        stmt = sa.select(KGSyncStateORM).where(KGSyncStateORM.entity_ref == entity_id)
        if kind is not None:
            stmt = stmt.where(KGSyncStateORM.entity_type == kind)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_sync_state(
        self,
        entity_id: str,
        kind: str,
        hash: str,
        source: str,
    ) -> KGSyncStateORM:
        """Insert or update a kg_sync_state row."""
        stmt = (
            pg_insert(KGSyncStateORM)
            .values(
                entity_type=kind,
                entity_ref=entity_id,
                content_hash=hash,
                source=source,
                status="ok",
            )
            .on_conflict_do_update(
                constraint="uq_kg_sync_state_entity",
                set_={
                    "content_hash": hash,
                    "source": source,
                    "synced_at": sa.func.now(),
                    "status": "ok",
                },
            )
            .returning(KGSyncStateORM)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def soft_delete_stale(self, seen_ids: set[str], source: str) -> list[str]:
        """Soft-delete source-owned concepts and edges not present in seen_ids."""
        deleted: list[str] = []
        deleted.extend(await self._soft_delete_stale_concepts(seen_ids, source))
        deleted.extend(await self._soft_delete_stale_edges(seen_ids, source))
        return deleted

    async def sync(
        self,
        concepts: Sequence[KGConcept],
        edges: Sequence[KGEdge],
    ) -> SyncReport:
        """Atomically sync concepts and edges into KG storage.

        The sync state is loaded in bulk, then diffed in memory to avoid N+1
        state queries. Manual entities are not auto-soft-deleted when omitted
        from a later run; generated sources are.
        """
        async with self._transaction():
            items = _sync_items(concepts, edges)
            state_map = await self._bulk_sync_state(items.keys())
            created: list[str] = []
            updated: list[str] = []
            unchanged: list[str] = []

            for key, item in items.items():
                current = state_map.get(key)
                label = f"{key[0]}:{key[1]}"
                if current is None:
                    created.append(label)
                elif current.content_hash != item["hash"]:
                    updated.append(label)
                else:
                    unchanged.append(label)

                if item["kind"] == "concept":
                    await self.upsert_concept(item["entity"])
                else:
                    await self.upsert_edge(item["entity"])
                await self.upsert_sync_state(
                    item["entity_id"],
                    item["kind"],
                    item["hash"],
                    item["source"],
                )

            soft_deleted = await self._soft_delete_auto_sources(items.values())
            await self.session.flush()

        return SyncReport(
            created=created,
            updated=updated,
            unchanged=unchanged,
            soft_deleted=soft_deleted,
        )

    @asynccontextmanager
    async def _transaction(self):
        """Open an atomic transaction or savepoint for already-managed sessions."""
        if self.session.in_transaction():
            async with self.session.begin_nested():
                yield
        else:
            async with self.session.begin():
                yield

    async def _bulk_sync_state(
        self,
        keys: Iterable[tuple[str, str]],
    ) -> dict[tuple[str, str], KGSyncStateORM]:
        """Bulk-select sync state rows for all entity keys."""
        key_list = list(keys)
        if not key_list:
            return {}
        result = await self.session.execute(
            sa.select(KGSyncStateORM).where(
                tuple_(KGSyncStateORM.entity_type, KGSyncStateORM.entity_ref).in_(key_list)
            )
        )
        rows = result.scalars().all()
        return {(row.entity_type, row.entity_ref): row for row in rows}

    async def _soft_delete_auto_sources(self, items: Iterable[dict[str, Any]]) -> list[str]:
        """Soft-delete stale non-manual entities for sources represented in storage."""
        seen_by_source: dict[str, set[str]] = {source: set() for source in _AUTO_SOFT_DELETE_SOURCES}
        for item in items:
            if item["source"] in _AUTO_SOFT_DELETE_SOURCES:
                seen_by_source[item["source"]].add(item["entity_id"])

        deleted: list[str] = []
        for source, seen in seen_by_source.items():
            deleted.extend(await self.soft_delete_stale(seen, source))
        return deleted

    async def _soft_delete_stale_concepts(self, seen_ids: set[str], source: str) -> list[str]:
        """Soft-delete stale concepts for one source."""
        stmt = sa.select(KGConceptORM).where(
            KGConceptORM.source == source,
            KGConceptORM.deleted_at.is_(None),
        )
        if seen_ids:
            stmt = stmt.where(sa.cast(KGConceptORM.id, sa.Text).not_in(seen_ids))
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())
        if not rows:
            return []

        ids = [row.id for row in rows]
        await self.session.execute(
            sa.update(KGConceptORM)
            .where(KGConceptORM.id.in_(ids))
            .values(is_deleted=True, deleted_at=sa.func.now(), updated_at=sa.func.now())
        )
        return [f"concept:{row.id}" for row in rows]

    async def _soft_delete_stale_edges(self, seen_ids: set[str], source: str) -> list[str]:
        """Soft-delete stale edges for one source."""
        result = await self.session.execute(
            sa.select(KGEdgeORM).where(
                KGEdgeORM.source == source,
                KGEdgeORM.deleted_at.is_(None),
            )
        )
        rows = [row for row in result.scalars().all() if edge_entity_ref(row) not in seen_ids]
        if not rows:
            return []

        ids = [row.id for row in rows]
        await self.session.execute(
            sa.update(KGEdgeORM)
            .where(KGEdgeORM.id.in_(ids))
            .values(is_deleted=True, deleted_at=sa.func.now(), updated_at=sa.func.now())
        )
        return [f"edge:{edge_entity_ref(row)}" for row in rows]


def _sync_items(
    concepts: Sequence[KGConcept],
    edges: Sequence[KGEdge],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Build sync metadata keyed by (entity_type, entity_ref)."""
    items: dict[tuple[str, str], dict[str, Any]] = {}
    for concept in concepts:
        entity_id = _concept_entity_ref(concept)
        items[("concept", entity_id)] = {
            "kind": "concept",
            "entity_id": entity_id,
            "entity": concept,
            "hash": canonical_hash(concept),
            "source": concept.source,
        }
    for edge in edges:
        entity_id = edge_entity_ref(edge)
        items[("edge", entity_id)] = {
            "kind": "edge",
            "entity_id": entity_id,
            "entity": edge,
            "hash": canonical_hash(edge),
            "source": edge.source,
        }
    return items
