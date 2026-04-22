"""CLI for the P1.5 sanitize/validate step."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from src.services.p1_artifact_sanitizer import sanitize_p1_artifacts

app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def main(
    input_dir: Path = typer.Option(..., "--input-dir", exists=True, file_okay=False, dir_okay=True),
    output_dir: Path = typer.Option(..., "--output-dir", file_okay=False, dir_okay=True),
    report_file: Path | None = typer.Option(None, "--report-file", file_okay=True, dir_okay=False),
) -> None:
    """Sanitize mechanical P1 artifact drift and block invalid files."""
    report = sanitize_p1_artifacts(input_dir=input_dir, output_dir=output_dir)
    typer.echo(json.dumps(report["summary"], ensure_ascii=False))

    if report_file is not None:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if report["summary"]["invalid_files"] > 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    sys.exit(app())
