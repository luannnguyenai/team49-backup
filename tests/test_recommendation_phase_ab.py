"""
tests/test_recommendation_phase_ab.py
--------------------------------------
Unit tests for Phase A/B split logic in the recommendation engine.

Run with:
    PYTHONPATH=. .venv/bin/python -m pytest tests/test_recommendation_phase_ab.py -v --noconftest
"""
from __future__ import annotations

import uuid
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers to build fake objects
# ---------------------------------------------------------------------------

def _make_unit(unit_id: uuid.UUID | None = None, section_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=unit_id or uuid.uuid4(),
        title="Unit Title",
        section_id=section_id or uuid.uuid4(),
        canonical_unit_id=str(uuid.uuid4()),
        estimated_minutes=30,
        course_id=uuid.uuid4(),
    )


def _make_placement(topic_unit_id: uuid.UUID, decision: str, score_pct: float = 55.0) -> SimpleNamespace:
    from decimal import Decimal
    return SimpleNamespace(
        topic_unit_id=topic_unit_id,
        decision=decision,
        score_pct=Decimal(str(score_pct)),
    )


def _make_user(user_id: uuid.UUID | None = None) -> SimpleNamespace:
    u = SimpleNamespace(id=user_id or uuid.uuid4())
    return u


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------

def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


# ---------------------------------------------------------------------------
# Core engine call with mocked deps
# ---------------------------------------------------------------------------

async def _run_engine(units, placement_results, mastery_by_kp=None):
    """
    Call _generate_canonical_learning_path with all external I/O mocked.
    Returns the GeneratePathResponse.
    """
    from src.services.recommendation_engine import _generate_canonical_learning_path
    from src.schemas.learning_path import GeneratePathRequest
    from src.models.learning import PathStatus

    user = _make_user()
    section_id = uuid.uuid4()
    for unit in units:
        unit.section_id = section_id

    fake_section = SimpleNamespace(title="Test Section", id=section_id)
    fake_course = SimpleNamespace(title="Test Course")
    fake_goal = SimpleNamespace(
        selected_course_ids=[uuid.uuid4()],
        derived_from_course_set_hash="abc123",
    )
    fake_plan = SimpleNamespace(id=uuid.uuid4())

    if mastery_by_kp is None:
        mastery_by_kp = {}

    request = GeneratePathRequest(desired_section_ids=[uuid.uuid4()])

    db = MagicMock()
    db.execute = AsyncMock()

    with (
        patch("src.services.recommendation_engine.CanonicalContentRepository") as MockContent,
        patch("src.services.recommendation_engine.GoalPreferenceRepository") as MockGoal,
        patch("src.services.recommendation_engine.LearnerMasteryKPRepository") as MockMastery,
        patch("src.services.recommendation_engine.PlacementAssessmentRepository") as MockPlacement,
        patch("src.services.recommendation_engine.PlannerAuditRepository") as MockAudit,
        patch("src.services.recommendation_engine.classify_unit_action", return_value="deep_practice"),
        patch("src.services.recommendation_engine.estimate_mastery_lcb_on_read", return_value=0.0),
    ):
        content_inst = MockContent.return_value
        content_inst.get_linked_learning_units = AsyncMock(return_value=units)
        content_inst.get_courses_by_ids = AsyncMock(
            return_value={unit.course_id: fake_course for unit in units}
        )
        content_inst.get_sections_by_ids = AsyncMock(return_value={section_id: fake_section})
        content_inst.get_unit_kp_rows = AsyncMock(return_value=[])
        content_inst.get_canonical_units_by_ids = AsyncMock(return_value={})
        content_inst.get_quiz_item_counts_by_unit_ids = AsyncMock(return_value={})
        content_inst.get_concepts_by_ids = AsyncMock(return_value={})
        content_inst.get_learning_units_by_ids = AsyncMock(return_value={u.id: u for u in units})

        goal_inst = MockGoal.return_value
        goal_inst.get_by_user_id = AsyncMock(return_value=fake_goal)

        mastery_inst = MockMastery.return_value
        mastery_inst.bulk_get_for_user = AsyncMock(return_value=mastery_by_kp)

        placement_inst = MockPlacement.return_value
        placement_inst.get_by_user_id = AsyncMock(return_value=placement_results)

        audit_inst = MockAudit.return_value
        audit_inst.create_plan = AsyncMock(return_value=fake_plan)
        audit_inst.add_rationale = AsyncMock()
        audit_inst.upsert_session_state = AsyncMock()

        # Also mock LearningProgressRepository and WaivedUnitRepository used in status map
        with (
            patch("src.services.recommendation_engine.LearningProgressRepository") as MockProgress,
            patch("src.services.recommendation_engine.WaivedUnitRepository") as MockWaived,
        ):
            MockProgress.return_value.list_for_user_units = AsyncMock(return_value={})
            MockWaived.return_value.list_for_user_units = AsyncMock(return_value={})

            response = await _generate_canonical_learning_path(db, user, request)

    return response


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestPhaseABSplit(unittest.IsolatedAsyncioTestCase):

    async def test_no_placement_results_all_items_no_phase(self):
        """Users with no placement results: all items get phase_tag=None, is_locked=False."""
        units = [_make_unit() for _ in range(3)]
        response = await _run_engine(units, placement_results=[])

        self.assertEqual(len(response.items), 3)
        for item in response.items:
            self.assertIsNone(item.phase_tag, f"Expected phase_tag=None, got {item.phase_tag}")
            self.assertFalse(item.is_locked, "Expected is_locked=False")
            self.assertIsNone(item.rationale_log)

    async def test_all_skip_all_phase_b_locked(self):
        """User with all 'skip' decisions → all items phase_b, is_locked=True."""
        unit_ids = [uuid.uuid4() for _ in range(3)]
        units = [_make_unit(uid) for uid in unit_ids]
        placements = [_make_placement(uid, "skip") for uid in unit_ids]

        response = await _run_engine(units, placement_results=placements)

        self.assertEqual(len(response.items), 3)
        for item in response.items:
            self.assertEqual(item.phase_tag, "phase_b")
            self.assertTrue(item.is_locked)
            self.assertIsNone(item.rationale_log)

    async def test_mixed_decisions_phase_a_first(self):
        """Mix of decisions: phase_a items appear before phase_b items."""
        uid_review = uuid.uuid4()
        uid_relearn = uuid.uuid4()
        uid_skip = uuid.uuid4()
        uid_unassessed = uuid.uuid4()

        units = [
            _make_unit(uid_review),
            _make_unit(uid_relearn),
            _make_unit(uid_skip),
            _make_unit(uid_unassessed),
        ]
        placements = [
            _make_placement(uid_review, "review"),
            _make_placement(uid_relearn, "relearn"),
            _make_placement(uid_skip, "skip"),
            # uid_unassessed has no placement row
        ]

        response = await _run_engine(units, placement_results=placements)

        items = response.items
        self.assertEqual(len(items), 4)

        phase_a_items = [i for i in items if i.phase_tag == "phase_a"]
        phase_b_items = [i for i in items if i.phase_tag == "phase_b"]

        self.assertEqual(len(phase_a_items), 3)  # review + relearn + unassessed
        self.assertEqual(len(phase_b_items), 1)  # skip

        # Phase A items must all come before phase B items
        phase_a_indices = [items.index(i) for i in phase_a_items]
        phase_b_indices = [items.index(i) for i in phase_b_items]
        self.assertLess(max(phase_a_indices), min(phase_b_indices))

        # Phase B item is locked
        for item in phase_b_items:
            self.assertTrue(item.is_locked)

        # Phase A items are not locked
        for item in phase_a_items:
            self.assertFalse(item.is_locked)

    async def test_rationale_log_populated_for_phase_a(self):
        """Phase A items have rationale_log; phase_b items do not."""
        uid_review = uuid.uuid4()
        uid_relearn = uuid.uuid4()
        uid_skip = uuid.uuid4()
        uid_unassessed = uuid.uuid4()

        units = [
            _make_unit(uid_review),
            _make_unit(uid_relearn),
            _make_unit(uid_skip),
            _make_unit(uid_unassessed),
        ]
        placements = [
            _make_placement(uid_review, "review"),
            _make_placement(uid_relearn, "relearn"),
            _make_placement(uid_skip, "skip"),
        ]

        response = await _run_engine(units, placement_results=placements)

        by_unit = {item.learning_unit_id: item for item in response.items}

        review_item = by_unit[uid_review]
        self.assertEqual(review_item.phase_tag, "phase_a")
        self.assertIsNotNone(review_item.rationale_log)
        self.assertIn("review", review_item.rationale_log)

        relearn_item = by_unit[uid_relearn]
        self.assertEqual(relearn_item.phase_tag, "phase_a")
        self.assertIsNotNone(relearn_item.rationale_log)
        self.assertIn("relearn", relearn_item.rationale_log)

        skip_item = by_unit[uid_skip]
        self.assertEqual(skip_item.phase_tag, "phase_b")
        self.assertIsNone(skip_item.rationale_log)

        unassessed_item = by_unit[uid_unassessed]
        self.assertEqual(unassessed_item.phase_tag, "phase_a")
        self.assertIsNotNone(unassessed_item.rationale_log)
        self.assertIn("prereq", unassessed_item.rationale_log)


if __name__ == "__main__":
    unittest.main()
