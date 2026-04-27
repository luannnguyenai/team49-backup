import unittest


class GoalCourseMapTests(unittest.TestCase):
    def test_goal_course_map_has_required_keys(self):
        from src.config.goal_course_map import GOAL_COURSE_MAP, GOAL_LABELS
        self.assertIn("computer_vision", GOAL_COURSE_MAP)
        self.assertIn("nlp", GOAL_COURSE_MAP)
        self.assertEqual(GOAL_COURSE_MAP["computer_vision"], "cs231n")
        self.assertEqual(GOAL_COURSE_MAP["nlp"], "cs224n")
        self.assertIn("computer_vision", GOAL_LABELS)
        self.assertIn("nlp", GOAL_LABELS)

    def test_valid_goal_ids_is_frozenset(self):
        from src.config.goal_course_map import VALID_GOAL_IDS
        self.assertIsInstance(VALID_GOAL_IDS, frozenset)
        self.assertIn("computer_vision", VALID_GOAL_IDS)
        self.assertIn("nlp", VALID_GOAL_IDS)

    def test_placement_result_model_importable(self):
        from src.models.placement import PlacementAssessmentResult
        self.assertTrue(hasattr(PlacementAssessmentResult, "__tablename__"))
        self.assertEqual(PlacementAssessmentResult.__tablename__, "placement_assessment_results")

    def test_placement_result_registered_in_init(self):
        import src.models as models
        self.assertTrue(hasattr(models, "PlacementAssessmentResult"))

    def test_placement_result_has_required_columns(self):
        from src.models.placement import PlacementAssessmentResult
        from sqlalchemy import inspect
        mapper = inspect(PlacementAssessmentResult)
        col_names = {c.key for c in mapper.columns}
        required = {"id", "user_id", "topic_unit_id", "score_pct", "decision",
                    "user_choice", "raw_answers", "theta_estimate", "created_at"}
        self.assertTrue(required.issubset(col_names), f"Missing columns: {required - col_names}")


if __name__ == "__main__":
    unittest.main()
