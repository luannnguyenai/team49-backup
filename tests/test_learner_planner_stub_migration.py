import unittest
from pathlib import Path


class LearnerPlannerStubMigrationTests(unittest.TestCase):
    def test_migration_mentions_all_planning_stub_tables(self):
        migration = Path(
            "alembic/versions/20260423_learner_planner_stub_persistence.py"
        ).read_text(encoding="utf-8")

        self.assertIn("plan_history", migration)
        self.assertIn("rationale_log", migration)
        self.assertIn("planner_session_state", migration)


if __name__ == "__main__":
    unittest.main()
