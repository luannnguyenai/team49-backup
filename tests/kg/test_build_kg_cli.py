"""Tests for the KG build CLI."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from typer.testing import CliRunner

from src.kg import pipeline
from src.kg.schemas import KGConcept, KGEdge
from src.kg.schemas import SyncReport
from src.scripts import build_kg


def test_build_kg_dry_run_does_not_call_sync(monkeypatch) -> None:
    """Dry-run mode builds but does not call repository sync."""
    sync_called = False

    async def fake_run_build_kg(*, dry_run: bool, phase: int):
        nonlocal sync_called
        assert dry_run is True
        assert phase == 0
        sync_called = True
        return SyncReport(created=[], updated=[], unchanged=["concept:1"], soft_deleted=[])

    monkeypatch.setattr(build_kg, "run_build_kg", fake_run_build_kg)

    result = CliRunner().invoke(build_kg.app, ["--dry-run", "--phase", "0"])

    assert result.exit_code == 0
    assert "unchanged" in result.output
    assert sync_called is True


@pytest.mark.asyncio
async def test_pipeline_dry_run_does_not_call_repository_sync(monkeypatch) -> None:
    """Dry-run pipeline returns a report without calling KGRepository.sync."""
    concept = KGConcept(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        name="Concept",
        source="manual",
    )
    edge = KGEdge(
        src_kind="kc",
        src_ref="KC-A",
        dst_kind="concept",
        dst_ref="CON-A",
        type="INSTANCE_OF",
        weight=1.0,
        source="manual",
    )

    async def fake_load_sources(session, data_dir):
        return SimpleNamespace()

    def fake_build(sources):
        return SimpleNamespace(concepts=(concept,), edges=(edge,))

    class FailingRepository:
        def __init__(self, session):
            pass

        async def sync(self, concepts, edges):
            raise AssertionError("sync must not be called during dry-run")

    monkeypatch.setattr(pipeline, "load_sources", fake_load_sources)
    monkeypatch.setattr(pipeline, "build", fake_build)
    monkeypatch.setattr(pipeline, "KGRepository", FailingRepository)

    report = await pipeline.run_build_kg(
        session=SimpleNamespace(),
        data_dir=SimpleNamespace(),
        phase=0,
        dry_run=True,
    )

    assert report.created == ()
    assert report.updated == ()
    assert report.soft_deleted == ()
    assert "concept:11111111-1111-4111-8111-111111111111" in report.unchanged
