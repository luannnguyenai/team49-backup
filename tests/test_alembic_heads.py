import subprocess
import unittest
from pathlib import Path
import ast


def _read_revision_ids() -> list[str]:
    revision_ids: list[str] = []
    for path in Path("alembic/versions").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("revision: str = "):
                revision_ids.append(ast.literal_eval(line.split("=", 1)[1].strip()))
                break
    return revision_ids


class AlembicHeadTests(unittest.TestCase):
    def test_alembic_has_single_head(self):
        result = subprocess.run(
            [".venv/bin/alembic", "heads"],
            check=True,
            capture_output=True,
            text=True,
        )
        heads = [line for line in result.stdout.strip().splitlines() if line.strip()]
        self.assertEqual(
            len(heads),
            1,
            f"Expected a single Alembic head, got {len(heads)}: {heads}",
        )

    def test_alembic_revision_ids_fit_version_column(self):
        for revision_id in _read_revision_ids():
            self.assertLessEqual(
                len(revision_id),
                32,
                f"Alembic revision id exceeds varchar(32): {revision_id}",
            )


if __name__ == "__main__":
    unittest.main()
