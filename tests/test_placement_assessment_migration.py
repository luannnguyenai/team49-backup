import unittest
from pathlib import Path


class PlacementAssessmentMigrationTests(unittest.TestCase):
    def test_migration_file_exists(self):
        files = list(Path("alembic/versions").glob("20260425_placement_asmnt.py"))
        self.assertEqual(len(files), 1, "Migration file 20260425_placement_asmnt.py not found")

    def test_revision_id_fits_varchar32(self):
        text = Path("alembic/versions/20260425_placement_asmnt.py").read_text()
        import ast
        for line in text.splitlines():
            if line.startswith("revision: str ="):
                rev_id = ast.literal_eval(line.split("=", 1)[1].strip())
                self.assertLessEqual(len(rev_id), 32, f"Revision ID too long: {rev_id}")
                break

    def test_migration_has_expected_content(self):
        text = Path("alembic/versions/20260425_placement_asmnt.py").read_text()
        for expected in [
            "placement_assessment_results",
            "score_pct",
            "theta_estimate",
            "ck_placement_results_decision",
            "ix_placement_results_user_unit",
            "20260424_resume_state",
        ]:
            self.assertIn(expected, text, f"Expected '{expected}' in migration file")


if __name__ == "__main__":
    unittest.main()
