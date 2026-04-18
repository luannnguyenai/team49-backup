import subprocess
import unittest


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


if __name__ == "__main__":
    unittest.main()
