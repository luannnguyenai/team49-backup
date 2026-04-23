from types import SimpleNamespace

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


def test_legacy_question_guard_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr(assessment_service.settings, "allow_legacy_question_reads", False)

    with pytest.raises(ValidationError, match="Legacy question reads are disabled"):
        assessment_service._ensure_legacy_question_reads_allowed()


def test_legacy_mastery_guard_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr(assessment_service.settings, "allow_legacy_mastery_writes", False)

    with pytest.raises(ValidationError, match="Legacy mastery writes are disabled"):
        assessment_service._ensure_legacy_mastery_writes_allowed()
