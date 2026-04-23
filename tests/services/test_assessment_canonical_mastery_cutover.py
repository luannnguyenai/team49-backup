from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.models.learning import SelectedAnswer
from src.schemas.assessment import AnswerInput
from src.services import assessment_service


def test_canonical_answer_batch_detection():
    assert assessment_service._is_canonical_answer_batch(
        [
            AnswerInput(canonical_item_id="item-1", selected_answer=SelectedAnswer.A),
            AnswerInput(canonical_item_id="item-2", selected_answer=SelectedAnswer.B),
        ]
    )
    assert not assessment_service._is_canonical_answer_batch(
        [AnswerInput(question_id=uuid4(), selected_answer=SelectedAnswer.A)]
    )


def test_selected_answer_to_index():
    assert assessment_service._selected_answer_to_index(SelectedAnswer.A) == 0
    assert assessment_service._selected_answer_to_index(SelectedAnswer.D) == 3


@pytest.mark.asyncio
async def test_submit_canonical_assessment_writes_interaction_and_mastery(monkeypatch):
    db = AsyncMock()
    db.add = Mock()

    item = Mock(item_id="item-1", answer_index=0)
    item_result = Mock()
    item_result.scalars.return_value.all.return_value = [item]
    seq_result = Mock()
    seq_result.scalar.return_value = 0
    db.execute.side_effect = [item_result, seq_result]

    updated = []

    async def fake_update_kp_mastery_from_item(db_arg, *, user_id, canonical_item_id, is_correct):
        updated.append((user_id, canonical_item_id, is_correct))
        return ["kp_attention"]

    monkeypatch.setattr(assessment_service.settings, "write_canonical_interactions_enabled", True)
    monkeypatch.setattr(assessment_service.settings, "write_learner_mastery_kp_enabled", True)
    monkeypatch.setattr(assessment_service, "update_kp_mastery_from_item", fake_update_kp_mastery_from_item)

    user_id = uuid4()
    session_id = uuid4()
    session = SimpleNamespace(
        completed_at=None,
        total_questions=0,
        correct_count=0,
        score_percent=None,
    )

    response = await assessment_service._submit_canonical_assessment(
        db=db,
        user_id=user_id,
        session=session,
        session_id=session_id,
        answers=[
            AnswerInput(
                canonical_item_id="item-1",
                selected_answer=SelectedAnswer.A,
                response_time_ms=1000,
            )
        ],
    )

    assert response.overall_score_percent == 100.0
    assert response.topic_results == []
    assert updated == [(user_id, "item-1", True)]
    interaction = db.add.call_args_list[0].args[0]
    assert interaction.question_id is None
    assert interaction.canonical_item_id == "item-1"
    assert db.flush.await_count == 1
