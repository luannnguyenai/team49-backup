"""Typer CLI for building and syncing the Knowledge Graph."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.database import async_session_factory
from src.kg.builder import CycleError
from src.kg.pipeline import run_build_kg as _run_pipeline
from src.kg.schemas import SyncReport

app = typer.Typer(add_completion=False)


def _logger() -> logging.Logger:
    try:
        import structlog  # type: ignore[import-not-found]
    except Exception:
        logging.basicConfig(
            level=settings.log_level,
            format='{"level":"%(levelname)s","event":"%(message)s"}',
        )
        return logging.getLogger("kg.build")

    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    return structlog.get_logger("kg.build")  # type: ignore[return-value]


async def run_build_kg(*, dry_run: bool, phase: int) -> SyncReport:
    """Open an async session and run the shared KG build pipeline."""
    async with async_session_factory() as session:
        return await _run_pipeline(
            session=session,
            data_dir=Path("data"),
            phase=phase,
            dry_run=dry_run,
        )


def _print_report(report: SyncReport) -> None:
    """Print a SyncReport as a rich table when available, plain text otherwise."""
    rows = [
        ("created", len(report.created), report.created),
        ("updated", len(report.updated), report.updated),
        ("unchanged", len(report.unchanged), report.unchanged),
        ("soft_deleted", len(report.soft_deleted), report.soft_deleted),
    ]
    try:
        from rich.console import Console
        from rich.table import Table
    except Exception:
        for name, count, values in rows:
            typer.echo(f"{name}\t{count}\t{', '.join(values)}")
        return

    table = Table(title="KG SyncReport")
    table.add_column("bucket")
    table.add_column("count", justify="right")
    table.add_column("ids")
    for name, count, values in rows:
        table.add_row(name, str(count), ", ".join(values))
    Console().print(table)


def _log_event(logger: Any, event: str, **kwargs: Any) -> None:
    """Log structured events with either structlog or stdlib logging."""
    if hasattr(logger, "info") and logger.__class__.__module__.startswith("structlog"):
        logger.info(event, **kwargs)
        return
    logger.info(json.dumps({"event": event, **kwargs}, ensure_ascii=False))


@app.callback(invoke_without_command=True)
def main(
    dry_run: bool = typer.Option(False, "--dry-run", help="Build without writing KG rows."),
    phase: int = typer.Option(settings.kg_phase, "--phase", min=0, max=1, help="KG build phase."),
) -> None:
    """Run the Knowledge Graph build/sync pipeline."""
    logger = _logger()
    try:
        _log_event(logger, "kg_build_start", dry_run=dry_run, phase=phase)
        report = asyncio.run(run_build_kg(dry_run=dry_run, phase=phase))
        _print_report(report)
        _log_event(logger, "kg_build_success", report=report.model_dump(mode="json"))
    except (CycleError, ValidationError, IntegrityError) as exc:
        _log_event(logger, "kg_build_failed", error=str(exc), error_type=type(exc).__name__)
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    sys.exit(app())
