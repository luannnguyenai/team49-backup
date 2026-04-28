"""
tests/test_phase_ab_lock.py
-----------------------------
Tests for:
  - Fix 1: rationale_log standardised format
  - Fix 2: multi-course Phase A round-robin interleave
  - Fix 3: Phase B is_locked dynamic gate

Run with:
    PYTHONPATH=. .venv/bin/python -m pytest tests/test_phase_ab_lock.py -v --noconftest
"""
from __future__ import annotations

import uuid
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_unit(
    unit_id: uuid.UUID | None = None,
    section_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=unit_id or uuid.uuid4(),
        title="Unit Title",
        section_id=section_id or uuid.uuid4(),
        canonical_unit_id=str(uuid.uuid4()),
        estimated_minutes=30,
        course_id=course_id or uuid.uuid4(),
    )


def _make_placement(
    topic_unit_id: uuid.UUID,
    decision: str,
    score_pct: float = 55.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        topic_unit_id=topic_unit_id,
        decision=decision,
        score_pct=Decimal(str(score_pct)),
    )


def _make_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value
    return _inner


async def _run_engine(units, placement_results, mastery_by_kp=None):
    from src.services.recommendation_engine import _generate_canonical_learning_path
    from src.schemas.learning_path import GeneratePathRequest

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
        patch("src.services.recommendation_engine.LearningProgressRepository") as MockProgress,
        patch("src.services.recommendation_engine.WaivedUnitRepository") as MockWaived,
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

        MockGoal.return_value.get_by_user_id = AsyncMock(return_value=fake_goal)
        MockMastery.return_value.bulk_get_for_user = AsyncMock(return_value=mastery_by_kp)
        MockPlacement.return_value.get_by_user_id = AsyncMock(return_value=placement_results)

        audit_inst = MockAudit.return_value
        audit_inst.create_plan = AsyncMock(return_value=fake_plan)
        audit_inst.add_rationale = AsyncMock()
        audit_inst.upsert_session_state = AsyncMock()

        MockProgress.return_value.list_for_user_units = AsyncMock(return_value={})
        MockWaived.return_value.list_for_user_units = AsyncMock(return_value={})

        response = await _generate_canonical_learning_path(db, user, request)

    return response


# ---------------------------------------------------------------------------
# Fix 1: rationale_log format
# ---------------------------------------------------------------------------

class TestRationaleLogFormat(unittest.IsolatedAsyncioTestCase):

    async def test_review_rationale_format(self):
        uid = uuid.uuid4()
        unit = _make_unit(uid)
        placement = _make_placement(uid, "review", score_pct=72.4)

        response = await _run_engine([unit], [placement])
        item = response.items[0]

        self.assertEqual(item.rationale_log, "placement_review_score=72")

    async def test_relearn_rationale_format(self):
        uid = uuid.uuid4()
        unit = _make_unit(uid)
        placement = _make_placement(uid, "relearn", score_pct=33.6)

        response = await _run_engine([unit], [placement])
        item = response.items[0]

        self.assertEqual(item.rationale_log, "placement_relearn_score=34")

    async def test_unassessed_rationale_format(self):
        """Units with no placement row get placement_prereq_unassessed."""
        uid = uuid.uuid4()
        unit = _make_unit(uid)
        # No placement entry for this unit
        response = await _run_engine([unit], [_make_placement(uuid.uuid4(), "skip")])
        item = response.items[0]

        self.assertEqual(item.phase_tag, "phase_a")
        self.assertEqual(item.rationale_log, "placement_prereq_unassessed")

    async def test_skip_rationale_is_none(self):
        uid = uuid.uuid4()
        unit = _make_unit(uid)
        placement = _make_placement(uid, "skip", score_pct=90.0)

        response = await _run_engine([unit], [placement])
        item = response.items[0]

        self.assertIsNone(item.rationale_log)

    async def test_score_rounding(self):
        """score_pct is rounded to nearest int."""
        uid = uuid.uuid4()
        unit = _make_unit(uid)
        placement = _make_placement(uid, "review", score_pct=49.5)

        response = await _run_engine([unit], [placement])
        item = response.items[0]

        # Python's round() uses banker's rounding: 49.5 -> 50
        self.assertEqual(item.rationale_log, f"placement_review_score={round(49.5)}")


# ---------------------------------------------------------------------------
# Fix 2: Multi-course round-robin interleave
# ---------------------------------------------------------------------------

class TestMultiCourseInterleave(unittest.IsolatedAsyncioTestCase):

    async def test_single_course_phase_a_preserved_order(self):
        """With one course, Phase A order is unchanged."""
        course_id = uuid.uuid4()
        uid1, uid2, uid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        units = [_make_unit(uid1, course_id=course_id),
                 _make_unit(uid2, course_id=course_id),
                 _make_unit(uid3, course_id=course_id)]
        placements = [
            _make_placement(uid1, "review"),
            _make_placement(uid2, "relearn"),
            _make_placement(uid3, "review"),
        ]

        response = await _run_engine(units, placements)
        phase_a_ids = [i.learning_unit_id for i in response.items if i.phase_tag == "phase_a"]
        self.assertEqual(phase_a_ids, [uid1, uid2, uid3])

    async def test_two_courses_interleaved(self):
        """3 cs231n + 2 cs224n → cs231n[0], cs224n[0], cs231n[1], cs224n[1], cs231n[2]."""
        course_a = uuid.uuid4()
        course_b = uuid.uuid4()

        a0, a1, a2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        b0, b1 = uuid.uuid4(), uuid.uuid4()

        units = [
            _make_unit(a0, course_id=course_a),
            _make_unit(a1, course_id=course_a),
            _make_unit(a2, course_id=course_a),
            _make_unit(b0, course_id=course_b),
            _make_unit(b1, course_id=course_b),
        ]
        placements = [
            _make_placement(a0, "review"),
            _make_placement(a1, "review"),
            _make_placement(a2, "review"),
            _make_placement(b0, "relearn"),
            _make_placement(b1, "relearn"),
        ]

        response = await _run_engine(units, placements)
        phase_a_ids = [i.learning_unit_id for i in response.items if i.phase_tag == "phase_a"]

        self.assertEqual(phase_a_ids, [a0, b0, a1, b1, a2])

    async def test_phase_b_appended_after_interleaved_phase_a(self):
        """Phase B items always follow all Phase A items."""
        course_a = uuid.uuid4()
        course_b = uuid.uuid4()
        uid_a = uuid.uuid4()
        uid_b = uuid.uuid4()
        uid_skip = uuid.uuid4()

        units = [
            _make_unit(uid_a, course_id=course_a),
            _make_unit(uid_b, course_id=course_b),
            _make_unit(uid_skip, course_id=course_a),
        ]
        placements = [
            _make_placement(uid_a, "review"),
            _make_placement(uid_b, "review"),
            _make_placement(uid_skip, "skip"),
        ]

        response = await _run_engine(units, placements)
        phase_a_indices = [i.order_index for i in response.items if i.phase_tag == "phase_a"]
        phase_b_indices = [i.order_index for i in response.items if i.phase_tag == "phase_b"]

        self.assertTrue(all(a < b for a in phase_a_indices for b in phase_b_indices))


# ---------------------------------------------------------------------------
# Fix 3: Dynamic Phase B gate
# ---------------------------------------------------------------------------

class TestPhaseBDynamicGate(unittest.IsolatedAsyncioTestCase):
    """Tests for _phase_b_unlocked helper directly."""

    async def _call_gate(self, phase_a_unit_ids, unit_by_id, unit_kp_rows, mastery_by_kp):
        from src.services.recommendation_engine import _phase_b_unlocked

        db = MagicMock()
        user_id = uuid.uuid4()

        with patch("src.services.recommendation_engine.LearnerMasteryKPRepository") as MockMastery:
            MockMastery.return_value.bulk_get_for_user = AsyncMock(return_value=mastery_by_kp)

            content_repo = MagicMock()
            content_repo.get_unit_kp_rows = AsyncMock(return_value=unit_kp_rows)

            result = await _phase_b_unlocked(
                db,
                user_id=user_id,
                phase_a_unit_ids=phase_a_unit_ids,
                unit_by_id=unit_by_id,
                content_repo=content_repo,
            )
        return result

    async def test_no_phase_a_unlocks_phase_b(self):
        result = await self._call_gate([], {}, [], {})
        self.assertTrue(result)

    async def test_all_phase_a_mastered_unlocks_phase_b(self):
        uid = uuid.uuid4()
        canonical_id = "cs231n_unit_01"
        unit = SimpleNamespace(canonical_unit_id=canonical_id)
        unit_by_id = {uid: unit}

        kp_row = SimpleNamespace(unit_id=canonical_id, kp_id="kp_1")

        # mastery LCB >= 0.7 — patch estimate_mastery_lcb_on_read to return 0.8
        with patch("src.services.recommendation_engine.estimate_mastery_lcb_on_read", return_value=0.8):
            mastery_obj = SimpleNamespace(theta_mu=1.0, theta_sigma=0.3, updated_at=datetime.now(UTC))
            result = await self._call_gate(
                [uid], unit_by_id, [kp_row], {"kp_1": mastery_obj}
            )
        self.assertTrue(result)

    async def test_phase_a_not_mastered_keeps_phase_b_locked(self):
        uid = uuid.uuid4()
        canonical_id = "cs231n_unit_01"
        unit = SimpleNamespace(canonical_unit_id=canonical_id)
        unit_by_id = {uid: unit}

        kp_row = SimpleNamespace(unit_id=canonical_id, kp_id="kp_1")

        with patch("src.services.recommendation_engine.estimate_mastery_lcb_on_read", return_value=0.5):
            mastery_obj = SimpleNamespace(theta_mu=0.0, theta_sigma=1.0, updated_at=datetime.now(UTC))
            result = await self._call_gate(
                [uid], unit_by_id, [kp_row], {"kp_1": mastery_obj}
            )
        self.assertFalse(result)

    async def test_no_mastery_records_treats_lcb_as_zero(self):
        """Unit with no mastery records → LCB=0 → Phase B stays locked."""
        uid = uuid.uuid4()
        canonical_id = "cs231n_unit_01"
        unit = SimpleNamespace(canonical_unit_id=canonical_id)
        unit_by_id = {uid: unit}

        kp_row = SimpleNamespace(unit_id=canonical_id, kp_id="kp_1")

        # mastery_by_kp is empty — no records for kp_1
        result = await self._call_gate([uid], unit_by_id, [kp_row], {})
        self.assertFalse(result)

    async def test_partial_mastery_keeps_locked(self):
        """One unit mastered, one not — Phase B stays locked."""
        uid1, uid2 = uuid.uuid4(), uuid.uuid4()
        c1, c2 = "unit_c1", "unit_c2"
        unit_by_id = {
            uid1: SimpleNamespace(canonical_unit_id=c1),
            uid2: SimpleNamespace(canonical_unit_id=c2),
        }
        kp_rows = [
            SimpleNamespace(unit_id=c1, kp_id="kp_a"),
            SimpleNamespace(unit_id=c2, kp_id="kp_b"),
        ]
        now = datetime.now(UTC)
        mastery_high = SimpleNamespace(theta_mu=2.0, theta_sigma=0.2, updated_at=now)
        mastery_low = SimpleNamespace(theta_mu=0.0, theta_sigma=1.5, updated_at=now)

        def fake_lcb(mastery, **kwargs):
            return 0.85 if mastery is mastery_high else 0.4

        with patch("src.services.recommendation_engine.estimate_mastery_lcb_on_read", side_effect=fake_lcb):
            result = await self._call_gate(
                [uid1, uid2], unit_by_id, kp_rows, {"kp_a": mastery_high, "kp_b": mastery_low}
            )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
