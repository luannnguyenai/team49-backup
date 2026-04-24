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

    def test_planning_stub_models_exist(self):
        from src.models.learning import PlanHistory, PlannerSessionState, RationaleLog

        self.assertEqual(PlanHistory.__tablename__, "plan_history")
        self.assertEqual(RationaleLog.__tablename__, "rationale_log")
        self.assertEqual(PlannerSessionState.__tablename__, "planner_session_state")

        self.assertTrue(hasattr(PlanHistory, "user_id"))
        self.assertTrue(hasattr(PlanHistory, "parent_plan_id"))
        self.assertTrue(hasattr(PlanHistory, "trigger"))
        self.assertTrue(hasattr(PlanHistory, "recommended_path_json"))
        self.assertTrue(hasattr(PlanHistory, "goal_snapshot_json"))
        self.assertTrue(hasattr(PlanHistory, "weights_used_json"))

        self.assertTrue(hasattr(RationaleLog, "plan_history_id"))
        self.assertTrue(hasattr(RationaleLog, "learning_unit_id"))
        self.assertTrue(hasattr(RationaleLog, "rank"))
        self.assertTrue(hasattr(RationaleLog, "reason_code"))
        self.assertTrue(hasattr(RationaleLog, "term_breakdown_json"))
        self.assertTrue(hasattr(RationaleLog, "rationale_text"))

        self.assertTrue(hasattr(PlannerSessionState, "user_id"))
        self.assertTrue(hasattr(PlannerSessionState, "session_id"))
        self.assertTrue(hasattr(PlannerSessionState, "last_plan_history_id"))
        self.assertTrue(hasattr(PlannerSessionState, "bridge_chain_depth"))
        self.assertTrue(hasattr(PlannerSessionState, "consecutive_bridge_count"))
        self.assertTrue(hasattr(PlannerSessionState, "state_json"))
        self.assertTrue(hasattr(PlannerSessionState, "current_unit_id"))
        self.assertTrue(hasattr(PlannerSessionState, "current_stage"))
        self.assertTrue(hasattr(PlannerSessionState, "current_progress"))
        self.assertTrue(hasattr(PlannerSessionState, "last_activity"))


if __name__ == "__main__":
    unittest.main()
