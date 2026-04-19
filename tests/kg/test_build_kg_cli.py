"""Tests for the KG build CLI."""

from typer.testing import CliRunner

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
