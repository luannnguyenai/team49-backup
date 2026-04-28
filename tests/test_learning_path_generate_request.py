from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_generate_learning_path_falls_back_to_request_selected_course_ids():
    from src.schemas.learning_path import GeneratePathRequest
    from src.services.recommendation_engine import _generate_canonical_learning_path

    section_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    unit = SimpleNamespace(
        id=unit_id,
        slug="lecture-01-seg1",
        title="Unit Title",
        section_id=section_id,
        canonical_unit_id=str(uuid.uuid4()),
        estimated_minutes=30,
        course_id=uuid.uuid4(),
    )
    section = SimpleNamespace(id=section_id, title="Deep Learning")
    course = SimpleNamespace(id=unit.course_id, slug="cs230", title="CS230: Deep Learning")
    plan = SimpleNamespace(id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock()

    with (
        patch("src.services.recommendation_engine.CanonicalContentRepository") as MockContent,
        patch("src.services.recommendation_engine.GoalPreferenceRepository") as MockGoal,
        patch("src.services.recommendation_engine.LearnerMasteryKPRepository") as MockMastery,
        patch("src.services.recommendation_engine.PlacementAssessmentRepository") as MockPlacement,
        patch("src.services.recommendation_engine.PlannerAuditRepository") as MockAudit,
        patch("src.services.recommendation_engine.LearningProgressRepository") as MockProgress,
        patch("src.services.recommendation_engine.WaivedUnitRepository") as MockWaived,
    ):
        content = MockContent.return_value
        content.get_linked_learning_units = AsyncMock(return_value=[unit])
        content.get_courses_by_ids = AsyncMock(return_value={unit.course_id: course})
        content.get_sections_by_ids = AsyncMock(return_value={section_id: section})
        content.get_unit_kp_rows = AsyncMock(return_value=[])
        content.get_canonical_units_by_ids = AsyncMock(return_value={})
        content.get_quiz_item_counts_by_unit_ids = AsyncMock(return_value={})
        content.get_concepts_by_ids = AsyncMock(return_value={})

        MockGoal.return_value.get_by_user_id = AsyncMock(return_value=None)
        MockMastery.return_value.bulk_get_for_user = AsyncMock(return_value={})
        MockPlacement.return_value.get_by_user_id = AsyncMock(return_value=[])
        MockProgress.return_value.list_for_user_units = AsyncMock(return_value={})
        MockWaived.return_value.list_for_user_units = AsyncMock(return_value={})

        audit = MockAudit.return_value
        audit.create_plan = AsyncMock(return_value=plan)
        audit.add_rationale = AsyncMock()
        audit.upsert_session_state = AsyncMock()

        response = await _generate_canonical_learning_path(
            db,
            user,
            GeneratePathRequest(selected_course_ids=["CS230", "CS231n"]),
        )

    content.get_linked_learning_units.assert_awaited_once_with(["CS230", "CS231n"])
    assert response.total_units == 1
    assert response.items[0].course_slug == "cs230"
    assert response.items[0].unit_slug == "lecture-01-seg1"
    assert response.items[0].learn_href == "/courses/cs230/learn/lecture-01-seg1"


@pytest.mark.asyncio
async def test_generate_learning_path_uses_placement_decision_for_action():
    from src.models.learning import PathAction
    from src.schemas.learning_path import GeneratePathRequest
    from src.services.recommendation_engine import _generate_canonical_learning_path

    section_id = uuid.uuid4()
    skip_unit_id = uuid.uuid4()
    relearn_unit_id = uuid.uuid4()
    unassessed_unit_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    course_id = uuid.uuid4()
    skip_unit = SimpleNamespace(
        id=skip_unit_id,
        title="Known Unit",
        section_id=section_id,
        canonical_unit_id="canonical-known",
        estimated_minutes=30,
        course_id=course_id,
    )
    relearn_unit = SimpleNamespace(
        id=relearn_unit_id,
        title="Needs Practice",
        section_id=section_id,
        canonical_unit_id="canonical-practice",
        estimated_minutes=45,
        course_id=course_id,
    )
    unassessed_unit = SimpleNamespace(
        id=unassessed_unit_id,
        title="Later Unit",
        section_id=section_id,
        canonical_unit_id="canonical-later",
        estimated_minutes=60,
        course_id=course_id,
    )
    section = SimpleNamespace(id=section_id, title="Deep Learning")
    course = SimpleNamespace(id=course_id, title="CS230: Deep Learning")
    plan = SimpleNamespace(id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock()

    with (
        patch("src.services.recommendation_engine.CanonicalContentRepository") as MockContent,
        patch("src.services.recommendation_engine.GoalPreferenceRepository") as MockGoal,
        patch("src.services.recommendation_engine.LearnerMasteryKPRepository") as MockMastery,
        patch("src.services.recommendation_engine.PlacementAssessmentRepository") as MockPlacement,
        patch("src.services.recommendation_engine.PlannerAuditRepository") as MockAudit,
        patch("src.services.recommendation_engine.LearningProgressRepository") as MockProgress,
        patch("src.services.recommendation_engine.WaivedUnitRepository") as MockWaived,
    ):
        content = MockContent.return_value
        content.get_linked_learning_units = AsyncMock(return_value=[skip_unit, relearn_unit, unassessed_unit])
        content.get_courses_by_ids = AsyncMock(return_value={course_id: course})
        content.get_sections_by_ids = AsyncMock(return_value={section_id: section})
        content.get_unit_kp_rows = AsyncMock(return_value=[])
        content.get_canonical_units_by_ids = AsyncMock(return_value={})
        content.get_quiz_item_counts_by_unit_ids = AsyncMock(return_value={})
        content.get_concepts_by_ids = AsyncMock(return_value={})

        MockGoal.return_value.get_by_user_id = AsyncMock(
            return_value=SimpleNamespace(selected_course_ids=["CS230"], placement_status=None),
        )
        MockMastery.return_value.bulk_get_for_user = AsyncMock(return_value={})
        MockPlacement.return_value.get_by_user_id = AsyncMock(
            return_value=[
                SimpleNamespace(topic_unit_id=skip_unit_id, decision="skip", score_pct=90.0),
                SimpleNamespace(topic_unit_id=relearn_unit_id, decision="relearn", score_pct=20.0),
            ],
        )
        MockProgress.return_value.list_for_user_units = AsyncMock(return_value={})
        MockWaived.return_value.list_for_user_units = AsyncMock(return_value={})

        audit = MockAudit.return_value
        audit.create_plan = AsyncMock(return_value=plan)
        audit.add_rationale = AsyncMock()
        audit.upsert_session_state = AsyncMock()

        response = await _generate_canonical_learning_path(
            db,
            user,
            GeneratePathRequest(selected_course_ids=["CS230"]),
        )

    by_title = {item.learning_unit_title: item for item in response.items}
    assert by_title["Known Unit"].action == PathAction.skip
    assert by_title["Known Unit"].estimated_hours is None
    assert by_title["Known Unit"].phase_tag == "phase_b"
    assert by_title["Known Unit"].is_locked is True
    assert by_title["Needs Practice"].action == PathAction.deep_practice
    assert by_title["Needs Practice"].estimated_hours == 0.75
    assert by_title["Needs Practice"].phase_tag == "phase_a"
    assert by_title["Later Unit"].action == PathAction.deep_practice
    assert by_title["Later Unit"].estimated_hours == 1.0
    assert by_title["Later Unit"].phase_tag == "phase_b"
    assert by_title["Later Unit"].is_locked is True

    saved_path = audit.create_plan.await_args.kwargs["recommended_path_json"]
    assert [item["learning_unit_id"] for item in saved_path] == [
        str(item.learning_unit_id) for item in response.items
    ]
    assert [item["order_index"] for item in saved_path] == [0, 1, 2]
    assert saved_path[0]["phase_tag"] == "phase_a"
