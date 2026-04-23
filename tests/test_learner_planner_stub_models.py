import unittest
from pathlib import Path

from src.models.learning import MasteryLevel


class LearnerPlannerStubModelTests(unittest.TestCase):
    def test_new_stub_models_exist_for_learner_mastery_and_goal_preferences(self):
        from src.models.learning import GoalPreference, LearnerMasteryKP

        self.assertEqual(LearnerMasteryKP.__tablename__, "learner_mastery_kp")
        self.assertEqual(GoalPreference.__tablename__, "goal_preferences")

        self.assertTrue(hasattr(LearnerMasteryKP, "user_id"))
        self.assertTrue(hasattr(LearnerMasteryKP, "kp_id"))
        self.assertTrue(hasattr(LearnerMasteryKP, "theta_mu"))
        self.assertTrue(hasattr(LearnerMasteryKP, "theta_sigma"))
        self.assertTrue(hasattr(LearnerMasteryKP, "mastery_mean_cached"))
        self.assertTrue(hasattr(LearnerMasteryKP, "n_items_observed"))
        self.assertTrue(hasattr(LearnerMasteryKP, "updated_by"))

        self.assertTrue(hasattr(GoalPreference, "user_id"))
        self.assertTrue(hasattr(GoalPreference, "goal_weights_json"))
        self.assertTrue(hasattr(GoalPreference, "selected_course_ids"))
        self.assertTrue(hasattr(GoalPreference, "goal_embedding"))
        self.assertTrue(hasattr(GoalPreference, "goal_embedding_version"))
        self.assertTrue(hasattr(GoalPreference, "derived_from_course_set_hash"))

    def test_stub_models_retain_existing_mastery_enum_contract(self):
        self.assertEqual(
            {item.value for item in MasteryLevel},
            {"not_started", "novice", "developing", "proficient", "mastered"},
        )

    def test_stub_migration_file_mentions_first_two_tables(self):
        migration = Path(
            "alembic/versions/20260423_learner_planner_stub_persistence.py"
        ).read_text(encoding="utf-8")

        self.assertIn("learner_mastery_kp", migration)
        self.assertIn("goal_preferences", migration)

    def test_waived_unit_stub_model_exists(self):
        from src.models.learning import WaivedUnit

        self.assertEqual(WaivedUnit.__tablename__, "waived_units")
        self.assertTrue(hasattr(WaivedUnit, "user_id"))
        self.assertTrue(hasattr(WaivedUnit, "learning_unit_id"))
        self.assertTrue(hasattr(WaivedUnit, "evidence_items"))
        self.assertTrue(hasattr(WaivedUnit, "mastery_lcb_at_waive"))
        self.assertTrue(hasattr(WaivedUnit, "skip_quiz_score"))

    def test_stub_migration_file_mentions_waived_units(self):
        migration = Path(
            "alembic/versions/20260423_learner_planner_stub_persistence.py"
        ).read_text(encoding="utf-8")

        self.assertIn("waived_units", migration)


if __name__ == "__main__":
    unittest.main()
