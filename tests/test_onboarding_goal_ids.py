# tests/test_onboarding_goal_ids.py
import unittest
from datetime import date


class OnboardingGoalIdsTests(unittest.TestCase):

    def test_onboarding_request_accepts_goal_ids(self):
        from src.schemas.auth import OnboardingRequest
        req = OnboardingRequest(
            goal_ids=["computer_vision", "nlp"],
            known_unit_ids=[],
            desired_section_ids=[],
            selected_course_ids=[],
            available_hours_per_week=5.0,
            target_deadline=date(2027, 1, 1),
            preferred_method="reading",
        )
        self.assertEqual(req.goal_ids, ["computer_vision", "nlp"])

    def test_onboarding_request_invalid_goal_id_raises(self):
        import pydantic
        from src.schemas.auth import OnboardingRequest
        with self.assertRaises(pydantic.ValidationError):
            OnboardingRequest(
                goal_ids=["invalid_goal"],
                known_unit_ids=[],
                desired_section_ids=[],
                selected_course_ids=[],
                available_hours_per_week=5.0,
                target_deadline=date(2027, 1, 1),
                preferred_method="reading",
            )

    def test_onboarding_request_empty_goal_ids_is_valid(self):
        from src.schemas.auth import OnboardingRequest
        req = OnboardingRequest(
            goal_ids=[],
            known_unit_ids=[],
            desired_section_ids=[],
            selected_course_ids=["cs231n"],
            available_hours_per_week=5.0,
            target_deadline=date(2027, 1, 1),
            preferred_method="video",
        )
        self.assertEqual(req.goal_ids, [])

    def test_goal_ids_map_to_course_ids(self):
        from src.config.goal_course_map import GOAL_COURSE_MAP
        self.assertEqual(GOAL_COURSE_MAP["computer_vision"], ["cs231n"])
        self.assertEqual(GOAL_COURSE_MAP["nlp"], ["cs224n"])
        self.assertEqual(GOAL_COURSE_MAP["deep_learning"], ["cs230"])

    def test_merged_course_ids_deduplication(self):
        # If goal_ids contains "computer_vision" (→ [cs231n]) and selected_course_ids
        # already has "cs231n", the merged list should not duplicate it.
        from src.config.goal_course_map import GOAL_COURSE_MAP
        goal_ids = ["computer_vision"]
        selected_course_ids = ["cs231n"]
        derived = [c for g in goal_ids if g in GOAL_COURSE_MAP for c in GOAL_COURSE_MAP[g]]
        merged = list(dict.fromkeys(selected_course_ids + derived))
        self.assertEqual(merged, ["cs231n"])  # no duplicate


if __name__ == "__main__":
    unittest.main()
