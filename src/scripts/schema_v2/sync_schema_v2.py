from __future__ import annotations

import argparse
import subprocess


def build_sync_commands(import_bundle: str | None) -> list[list[str]]:
    commands: list[list[str]] = [["alembic", "upgrade", "head"]]
    if import_bundle:
        commands.append(
            [
                "python",
                "-m",
                "src.scripts.pipeline.import_canonical_artifacts_to_db",
                "--input-dir",
                import_bundle,
            ]
        )
    commands.extend(
        [
            [
                "python",
                "-m",
                "src.scripts.schema_v2.backfill_schema_v2",
                "--apply",
                "--report-path",
                "reports/schema_v2_backfill_report.json",
            ],
            [
                "python",
                "-m",
                "src.scripts.schema_v2.validate_schema_v2",
                "--report-path",
                "reports/schema_v2_validation_report.json",
            ],
            ["python", "-m", "src.scripts.pipeline.check_canonical_runtime_parity"],
        ]
    )
    return commands


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync local DB to full Schema v2 shape without rerunning ingest."
    )
    parser.add_argument(
        "--import-bundle",
        default=None,
        help="Optional canonical bundle dir to import before Schema v2 backfill.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without running them."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = build_sync_commands(args.import_bundle)
    for command in commands:
        print("+", " ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
