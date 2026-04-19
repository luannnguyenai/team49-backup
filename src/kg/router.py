"""FastAPI router for Knowledge Graph operations."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, settings
from src.database import async_session_factory, get_async_db
from src.kg.builder import CycleError
from src.kg.models import KGConceptORM, KGEdgeORM, KGSyncStateORM
from src.kg.pipeline import run_build_kg as _run_pipeline
from src.kg.providers import DBMasteryProvider
from src.kg.schemas import LearningPath, RankedCandidate, SyncReport, TopicContext
from src.kg.service import KGService

router = APIRouter(prefix="/kg", tags=["kg"])


class KGSyncRequest(BaseModel):
    """Request body for KG sync."""

    phase: int | None = Field(default=None, ge=0, le=1)


class KGPathRequest(BaseModel):
    """Request body for KG path building."""

    user_id: uuid.UUID
    target_topics: list[str] = Field(min_length=1)
    hours_per_week: float = Field(gt=0)


def get_settings() -> Settings:
    """Dependency wrapper for settings."""
    return settings


def get_kg_service() -> KGService:
    """Create the DB-backed KG read service."""
    mastery = DBMasteryProvider(async_session_factory)
    return KGService(session_factory=async_session_factory, mastery=mastery, repo=None)


async def require_admin(
    config: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Require a matching X-Admin-Token header."""
    if not config.admin_token or x_admin_token != config.admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


async def run_build_kg(
    db: AsyncSession,
    config: Settings,
    body: KGSyncRequest | None = None,
) -> SyncReport:
    """Dependency that runs the KG pipeline for the sync route."""
    phase = body.phase if body and body.phase is not None else config.kg_phase
    return await _run_pipeline(session=db, data_dir=Path("data"), phase=phase)


async def get_kg_health(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> dict:
    """Return KG node/edge counts and last sync timestamp."""
    concept_count = (
        await db.execute(
            sa.select(sa.func.count()).select_from(KGConceptORM).where(KGConceptORM.deleted_at.is_(None))
        )
    ).scalar_one()
    edge_rows = (
        await db.execute(
            sa.select(KGEdgeORM.type, sa.func.count())
            .where(KGEdgeORM.deleted_at.is_(None))
            .group_by(KGEdgeORM.type)
        )
    ).all()
    last_sync_at = (
        await db.execute(sa.select(sa.func.max(KGSyncStateORM.synced_at)))
    ).scalar_one()
    return {
        "node_counts_by_kind": {"concept": concept_count},
        "edge_counts_by_type": {row[0]: row[1] for row in edge_rows},
        "last_sync_at": last_sync_at.isoformat() if last_sync_at else None,
    }


@router.post("/sync", response_model=SyncReport)
async def sync_kg(
    _admin: Annotated[None, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    config: Annotated[Settings, Depends(get_settings)],
    body: KGSyncRequest | None = None,
) -> SyncReport:
    """Run KG sync."""
    try:
        return await run_build_kg(db=db, config=config, body=body)
    except (CycleError, ValidationError, IntegrityError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def kg_health(payload: Annotated[dict, Depends(get_kg_health)]) -> dict:
    """Return KG health metrics."""
    return payload


@router.get("/topic/{slug}/context", response_model=TopicContext)
async def kg_topic_context(
    slug: str,
    service: Annotated[KGService, Depends(get_kg_service)],
    hops: int = 2,
) -> TopicContext:
    """Return KG context for one topic."""
    try:
        return await service.get_topic_context(slug, hops=hops)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Topic not found: {slug}") from exc


@router.post("/path", response_model=LearningPath)
async def kg_path(
    body: KGPathRequest,
    service: Annotated[KGService, Depends(get_kg_service)],
) -> LearningPath:
    """Build a KG learning path for a user and target topics."""
    try:
        return await service.build_path(
            user_id=body.user_id,
            target_topics=body.target_topics,
            hours_per_week=body.hours_per_week,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Topic not found: {exc.args[0]}") from exc


@router.get("/recommend/next", response_model=list[RankedCandidate])
async def kg_recommend_next(
    user_id: uuid.UUID,
    service: Annotated[KGService, Depends(get_kg_service)],
    candidate_limit: int = 20,
) -> list[RankedCandidate]:
    """Rank next candidate topics for a user."""
    return await service.rank_next(user_id=user_id, candidate_limit=candidate_limit)
