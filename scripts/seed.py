"""
Canonical bootstrap entrypoint.

The old `modules/topics/questions` seed flow was removed with the legacy runtime
tables. This script now imports canonical JSONL artifacts and the product course
shell so existing `make seed` / startup scripts keep using one stable command.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import async_session  # noqa: E402
from src.scripts.pipeline.check_canonical_runtime_parity import build_parity_report  # noqa: E402
from src.scripts.pipeline.import_canonical_artifacts_to_db import (  # noqa: E402
    DEFAULT_INPUT_DIR,
    import_canonical_artifacts,
    validate_canonical_artifacts,
)
from src.scripts.pipeline.import_product_shell_to_db import (  # noqa: E402
    build_product_shell_bundle,
    import_product_shell,
)


async def run_seed(*, input_dir: Path = DEFAULT_INPUT_DIR, validate_only: bool = False) -> dict[str, Any]:
    """Import canonical content and product shell, or validate both without writes."""
    if validate_only:
        canonical_report = validate_canonical_artifacts(input_dir)
        canonical_report.pop("_loaded_rows", None)
        product_bundle = build_product_shell_bundle()
        return {
            "mode": "validate_only",
            "canonical": canonical_report,
            "product_shell": {
                "counts": {table_name: len(rows) for table_name, rows in product_bundle.items()}
            },
        }

    async with async_session() as session:
        canonical_report = await import_canonical_artifacts(session=session, input_dir=input_dir)
        product_report = await import_product_shell(session=session)
        parity_report = await build_parity_report(session)
        await session.commit()

    return {
        "mode": "import",
        "canonical": canonical_report,
        "product_shell": product_report,
        "parity": parity_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import canonical content artifacts and product shell rows."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument(
        "--dry-run",
        "--validate-only",
        action="store_true",
        dest="validate_only",
        help="Validate canonical/product-shell inputs without writing to the database.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Rejected. Legacy destructive reseed is no longer supported.",
    )
    args = parser.parse_args()

    if args.clear:
        parser.error(
            "--clear was removed with legacy modules/topics/questions. "
            "Use Alembic/database reset plus canonical import if a full reset is required."
        )

    report = asyncio.run(run_seed(input_dir=args.input_dir, validate_only=args.validate_only))
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
