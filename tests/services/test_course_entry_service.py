import types
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from src.services.course_entry_service import get_start_learning_decision


class CourseEntryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_learning_ready_routes_to_first_canonical_unit(self):
        user = types.SimpleNamespace(
            id=uuid.uuid4(),
            is_onboarded=True,
        )

        with patch(
            "src.services.course_entry_service._check_skill_test_completed",
            new=AsyncMock(return_value=True),
        ):
            result = await get_start_learning_decision("cs231n", user=user)

        self.assertIsNotNone(result)
        self.assertEqual(result.reason, "learning_ready")
        self.assertIn(
            result.target,
            {
                "/courses/cs231n/learn/lecture-1-introduction-seg1",
                "/courses/cs231n",
            },
        )

    async def test_beginner_skipped_placement_can_start_without_completed_assessment(self):
        user = types.SimpleNamespace(
            id=uuid.uuid4(),
            is_onboarded=True,
        )

        with (
            patch(
                "src.services.course_entry_service._check_skill_test_completed",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "src.services.course_entry_service._check_placement_skipped",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await get_start_learning_decision("cs231n", user=user)

        self.assertIsNotNone(result)
        self.assertEqual(result.reason, "learning_ready")
        self.assertIn(
            result.target,
            {
                "/courses/cs231n/learn/lecture-1-introduction-seg1",
                "/courses/cs231n",
            },
        )

    async def test_non_skipped_user_without_assessment_still_routes_to_assessment(self):
        user = types.SimpleNamespace(
            id=uuid.uuid4(),
            is_onboarded=True,
        )

        with (
            patch(
                "src.services.course_entry_service._check_skill_test_completed",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "src.services.course_entry_service._check_placement_skipped",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await get_start_learning_decision("cs231n", user=user)

        self.assertIsNotNone(result)
        self.assertEqual(result.reason, "skill_test_required")
        self.assertEqual(
            result.target,
            "/assessment?next=/courses/cs231n/start",
        )
