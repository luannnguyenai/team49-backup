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
        title="Unit Title",
        section_id=section_id,
        canonical_unit_id=str(uuid.uuid4()),
        estimated_minutes=30,
        course_id=uuid.uuid4(),
    )
    section = SimpleNamespace(id=section_id, title="Deep Learning")
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
