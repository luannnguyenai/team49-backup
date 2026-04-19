"""Shared KG build pipeline used by CLI and API routes."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.kg.builder import build
from src.kg.discoverer import get_discoverer
from src.kg.loader import load_sources
from src.kg.repository import KGRepository
from src.kg.schemas import SyncReport


async def run_build_kg(
    *,
    session: AsyncSession,
    data_dir: Path,
    phase: int,
    dry_run: bool = False,
) -> SyncReport:
    """Load, build, optionally discover alignments, and sync the KG."""
    sources = await load_sources(session, data_dir)
    result = build(sources)
    edges = list(result.edges)

    if phase >= 1:
        discoverer = get_discoverer(settings)
        edges.extend(discoverer.discover(sources, manual_edges=edges))

    if dry_run:
        return SyncReport(
            created=[],
            updated=[],
            unchanged=[
                *(f"concept:{concept.id}" for concept in result.concepts),
                *(
                    f"edge:{edge.src_kind}:{edge.src_ref}->{edge.dst_kind}:{edge.dst_ref}:{edge.type}"
                    for edge in edges
                ),
            ],
            soft_deleted=[],
        )

    return await KGRepository(session).sync(result.concepts, edges)
