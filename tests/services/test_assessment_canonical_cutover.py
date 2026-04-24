from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.services import assessment_service


@pytest.mark.asyncio
async def test_select_canonical_questions_for_units_uses_phase(monkeypatch):
    captured = {}
    selected = SimpleNamespace(
        item_id="lecture01-q1",
        question="What is NLP?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        difficulty="medium",
        unit_id="local::lecture01::seg1",
    )

    class FakeSelector:
        def __init__(self, repo):
            captured["repo"] = repo

        async def select_for_phase(self, *, phase, canonical_unit_ids, kp_ids=None, count=5):
            captured["phase"] = phase
            captured["canonical_unit_ids"] = canonical_unit_ids
            captured["kp_ids"] = kp_ids
            captured["count"] = count
            return [selected]

    monkeypatch.setattr(assessment_service, "CanonicalQuestionSelector", FakeSelector)
    monkeypatch.setattr(assessment_service, "CanonicalQuestionRepository", lambda db: "canonical-repo")

    result = await assessment_service._select_canonical_questions_for_units(
        db=object(),
        canonical_unit_ids=["local::lecture01::seg1"],
        phase="placement",
        count=1,
    )

    assert result == [selected]
    assert captured["repo"] == "canonical-repo"
    assert captured["phase"] == "placement"
    assert captured["canonical_unit_ids"] == ["local::lecture01::seg1"]


def test_canonical_question_payload_preserves_item_and_unit_ids():
    item = SimpleNamespace(
        item_id="lecture01-q1",
        question="What is NLP?",
        choices=["A", "B", "C", "D"],
        difficulty="medium",
        unit_id="local::lecture01::seg1",
    )

    payload = assessment_service._canonical_item_to_assessment_question(item)

    assert payload.item_id == "lecture01-q1"
    assert payload.canonical_item_id == "lecture01-q1"
    assert payload.canonical_unit_id == "local::lecture01::seg1"
    assert payload.stem_text == "What is NLP?"


@pytest.mark.asyncio
async def test_assessment_requires_canonical_unit_ids():
    db = AsyncMock()

    with pytest.raises(ValidationError, match="canonical_unit_ids"):
        await assessment_service._resolve_canonical_unit_ids(
            db,
            learning_unit_ids=[],
            canonical_unit_ids=None,
        )


@pytest.mark.asyncio
async def test_build_canonical_assessment_response_groups_by_learning_unit():
    unit_id = uuid4()
    completed_at = datetime.now(UTC)
    db = AsyncMock()

    unit = SimpleNamespace(id=unit_id, canonical_unit_id="unit-1", title="Backpropagation")
    db.execute.side_effect = [
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [unit])),
        SimpleNamespace(
            all=lambda: [
                ("unit-1", "Chain rule"),
                ("unit-1", "Gradients"),
            ]
        ),
    ]

    rows = [
        (
            SimpleNamespace(is_correct=True),
            SimpleNamespace(item_id="item-1", unit_id="unit-1"),
        ),
        (
            SimpleNamespace(is_correct=False),
            SimpleNamespace(item_id="item-2", unit_id="unit-1"),
        ),
    ]

    response = await assessment_service._build_canonical_assessment_response(
        db=db,
        session_id=uuid4(),
        completed_at=completed_at,
        rows=rows,
    )

    assert response.overall_score_percent == 50.0
    assert len(response.learning_unit_results) == 1
    assert response.learning_unit_results[0].learning_unit_id == unit_id
    assert response.learning_unit_results[0].learning_unit_title == "Backpropagation"
    assert response.learning_unit_results[0].weak_kcs == ["Chain rule", "Gradients"]
