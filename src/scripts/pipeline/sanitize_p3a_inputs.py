"""CLI for mechanical sanitization of Prompt 3a input artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.services.p3_input_sanitizer import sanitize_p3a_artifacts


def main(*, input_dir: Path, output_dir: Path | None, report_file: Path | None) -> None:
    """Sanitize mechanical placeholder drift in p3a inputs."""
    target_dir = output_dir or input_dir
    report = sanitize_p3a_artifacts(input_dir=input_dir, output_dir=target_dir)
    print(json.dumps(report["summary"], ensure_ascii=False))

    if report_file is not None:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanitize mechanical placeholder drift in p3a inputs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--report-file")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    main(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        report_file=Path(args.report_file) if args.report_file else None,
    )
