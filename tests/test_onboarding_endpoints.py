"""
tests/test_onboarding_endpoints.py
-----------------------------------
Unit tests for onboarding schemas and service logic (no DB).
Run with:
  PYTHONPATH=. .venv/bin/python -m pytest tests/test_onboarding_endpoints.py -v --noconftest
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from src.schemas.onboarding import (
    GoalsRequest,
    GoalsResponse,
    KnownTopicsRequest,
    KnownTopicsResponse,
    TopicsResponse,
    UnitSummary,
    SectionSummary,
    CourseSummary,
)
from src.services.onboarding_service import (
    _derive_course_ids,
    _all_course_ids,
    _COURSE_TO_GOAL,
    save_user_goals,
    save_known_topics,
)
from src.config.goal_course_map import GOAL_COURSE_MAP, VALID_GOAL_IDS


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestGoalsRequestSchema(unittest.TestCase):
    def test_valid_single_goal(self):
        req = GoalsRequest(goal_ids=["computer_vision"])
        self.assertEqual(req.goal_ids, ["computer_vision"])

    def test_valid_multiple_goals(self):
        req = GoalsRequest(goal_ids=["nlp", "deep_learning"])
        self.assertEqual(len(req.goal_ids), 2)

    def test_invalid_goal_raises(self):
        with self.assertRaises(ValidationError):
            GoalsRequest(goal_ids=["made_up_goal"])

    def test_empty_list_raises(self):
        with self.assertRaises(ValidationError):
            GoalsRequest(goal_ids=[])

    def test_mixed_valid_invalid_raises(self):
        with self.assertRaises(ValidationError):
            GoalsRequest(goal_ids=["nlp", "not_real"])

    def test_all_valid_goal_ids(self):
        req = GoalsRequest(goal_ids=list(VALID_GOAL_IDS))
        self.assertEqual(set(req.goal_ids), VALID_GOAL_IDS)


class TestKnownTopicsRequestSchema(unittest.TestCase):
    def test_valid_uuids(self):
        uid1, uid2 = uuid4(), uuid4()
        req = KnownTopicsRequest(topic_unit_ids=[uid1, uid2])
        self.assertEqual(len(req.topic_unit_ids), 2)

    def test_empty_list_is_valid(self):
        req = KnownTopicsRequest(topic_unit_ids=[])
        self.assertEqual(req.topic_unit_ids, [])

    def test_invalid_uuid_raises(self):
        with self.assertRaises(ValidationError):
            KnownTopicsRequest(topic_unit_ids=["not-a-uuid"])


class TestGoalsResponseSchema(unittest.TestCase):
    def test_round_trip(self):
        resp = GoalsResponse(goal_ids=["nlp"], course_ids=["cs224n"])
        data = resp.model_dump()
        self.assertEqual(data["goal_ids"], ["nlp"])
        self.assertEqual(data["course_ids"], ["cs224n"])


class TestTopicsResponseSchema(unittest.TestCase):
    def test_empty_courses(self):
        resp = TopicsResponse(courses=[])
        self.assertEqual(resp.courses, [])

    def test_nested_structure(self):
        uid = uuid4()
        sid = uuid4()
        resp = TopicsResponse(
            courses=[
                CourseSummary(
                    course_id="cs231n",
                    goal_id="computer_vision",
                    sections=[
                        SectionSummary(
                            section_id=sid,
                            title="Module 1",
                            units=[
                                UnitSummary(
                                    unit_id=uid,
                                    title="Intro to CNNs",
                                    estimated_hours_beginner=1.5,
                                )
                            ],
                        )
                    ],
                )
            ]
        )
        self.assertEqual(resp.courses[0].course_id, "cs231n")
        self.assertEqual(resp.courses[0].sections[0].units[0].estimated_hours_beginner, 1.5)


# ---------------------------------------------------------------------------
# Service logic tests (pure functions)
# ---------------------------------------------------------------------------

class TestDeriveCourseIds(unittest.TestCase):
    def test_single_goal(self):
        result = _derive_course_ids(["computer_vision"])
        self.assertEqual(result, GOAL_COURSE_MAP["computer_vision"])

    def test_multiple_goals_deduped(self):
        result = _derive_course_ids(["nlp", "deep_learning"])
        # No duplicates
        self.assertEqual(len(result), len(set(result)))

    def test_unknown_goal_returns_empty(self):
        result = _derive_course_ids(["nonexistent"])
        self.assertEqual(result, [])

    def test_empty_returns_empty(self):
        result = _derive_course_ids([])
        self.assertEqual(result, [])

    def test_all_valid_goals(self):
        result = _derive_course_ids(list(VALID_GOAL_IDS))
        self.assertTrue(len(result) > 0)
        # All results are known course_ids
        all_known = {c for cids in GOAL_COURSE_MAP.values() for c in cids}
        for cid in result:
            self.assertIn(cid, all_known)


class TestAllCourseIds(unittest.TestCase):
    def test_returns_all_unique(self):
        result = _all_course_ids()
        self.assertEqual(len(result), len(set(result)))
        all_expected = {c for cids in GOAL_COURSE_MAP.values() for c in cids}
        self.assertEqual(set(result), all_expected)


class TestCourseToGoalMap(unittest.TestCase):
    def test_known_courses_mapped(self):
        for goal, courses in GOAL_COURSE_MAP.items():
            for cid in courses:
                self.assertIn(cid, _COURSE_TO_GOAL)

    def test_cs231n_maps_to_computer_vision(self):
        self.assertEqual(_COURSE_TO_GOAL.get("cs231n"), "computer_vision")

    def test_cs224n_maps_to_nlp(self):
        self.assertEqual(_COURSE_TO_GOAL.get("cs224n"), "nlp")


# ---------------------------------------------------------------------------
# Service async tests (mocked DB)
# ---------------------------------------------------------------------------

class TestSaveUserGoals(unittest.IsolatedAsyncioTestCase):
    async def test_save_goals_calls_upsert_and_commit(self):
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        fake_pref = MagicMock()
        mock_repo.upsert_for_user.return_value = fake_pref

        with patch(
            "src.services.onboarding_service.GoalPreferenceRepository",
            return_value=mock_repo,
        ):
            result = await save_user_goals(mock_db, user_id=uuid4(), goal_ids=["nlp"])

        mock_repo.upsert_for_user.assert_called_once()
        mock_db.commit.assert_called_once()
        self.assertEqual(result.goal_ids, ["nlp"])
        self.assertEqual(result.course_ids, ["cs224n"])

    async def test_save_goals_derives_correct_courses(self):
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.upsert_for_user.return_value = MagicMock()

        with patch(
            "src.services.onboarding_service.GoalPreferenceRepository",
            return_value=mock_repo,
        ):
            result = await save_user_goals(
                mock_db,
                user_id=uuid4(),
                goal_ids=["computer_vision", "nlp"],
            )

        expected = _derive_course_ids(["computer_vision", "nlp"])
        self.assertEqual(result.course_ids, expected)


class TestSaveKnownTopics(unittest.IsolatedAsyncioTestCase):
    async def test_saves_unit_ids_in_notes(self):
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id.return_value = None  # No existing record
        mock_repo.upsert_for_user.return_value = MagicMock()

        uid1, uid2 = uuid4(), uuid4()

        with patch(
            "src.services.onboarding_service.GoalPreferenceRepository",
            return_value=mock_repo,
        ):
            result = await save_known_topics(
                mock_db, user_id=uuid4(), topic_unit_ids=[uid1, uid2]
            )

        self.assertTrue(result.saved)
        self.assertEqual(result.count, 2)
        mock_db.commit.assert_called_once()

        # Verify notes JSON contains the unit IDs
        call_kwargs = mock_repo.upsert_for_user.call_args
        notes_str = call_kwargs.kwargs.get("notes") or call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs["notes"]
        notes = json.loads(notes_str)
        self.assertIn("known_unit_ids", notes)
        saved_ids = set(notes["known_unit_ids"])
        self.assertIn(str(uid1), saved_ids)
        self.assertIn(str(uid2), saved_ids)

    async def test_merges_with_existing_notes(self):
        mock_db = AsyncMock()
        mock_repo = AsyncMock()

        existing_uid = uuid4()
        existing = MagicMock()
        existing.notes = json.dumps({"known_unit_ids": [str(existing_uid)]})
        mock_repo.get_by_user_id.return_value = existing
        mock_repo.upsert_for_user.return_value = MagicMock()

        new_uid = uuid4()

        with patch(
            "src.services.onboarding_service.GoalPreferenceRepository",
            return_value=mock_repo,
        ):
            result = await save_known_topics(
                mock_db, user_id=uuid4(), topic_unit_ids=[new_uid]
            )

        self.assertEqual(result.count, 2)  # old + new

    async def test_deduplicates_unit_ids(self):
        mock_db = AsyncMock()
        mock_repo = AsyncMock()

        shared_uid = uuid4()
        existing = MagicMock()
        existing.notes = json.dumps({"known_unit_ids": [str(shared_uid)]})
        mock_repo.get_by_user_id.return_value = existing
        mock_repo.upsert_for_user.return_value = MagicMock()

        with patch(
            "src.services.onboarding_service.GoalPreferenceRepository",
            return_value=mock_repo,
        ):
            result = await save_known_topics(
                mock_db, user_id=uuid4(), topic_unit_ids=[shared_uid]
            )

        # Same ID submitted again → still count 1
        self.assertEqual(result.count, 1)


if __name__ == "__main__":
    unittest.main()
