from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services import assessment_service


@pytest.mark.asyncio
async def test_select_questions_for_topic_uses_question_selector(monkeypatch):
    """Assessment selection phải đi qua QuestionSelector để giữ một chiến lược chung."""
    topic_id = uuid4()
    excluded_ids = {uuid4()}
    selected_question = SimpleNamespace(id=uuid4())
    captured: dict[str, object] = {}

    class FakeSelector:
        def __init__(self, repo):
            captured["repo"] = repo

        async def select_by_bloom_irt(self, *, user_id, topic_id, slots, ability, excluded_ids):
            captured["user_id"] = user_id
            captured["topic_id"] = topic_id
            captured["slots"] = slots
            captured["ability"] = ability
            captured["excluded_ids"] = excluded_ids
            return [selected_question]

    monkeypatch.setattr(assessment_service, "QuestionRepository", lambda db: "question-repo")
    monkeypatch.setattr(assessment_service, "QuestionSelector", FakeSelector)

    result = await assessment_service._select_questions_for_topic(
        db=object(),
        user_id=uuid4(),
        topic_id=topic_id,
        excluded_ids=excluded_ids,
        ability=1.25,
    )

    assert result == [selected_question]
    assert captured["repo"] == "question-repo"
    assert captured["topic_id"] == topic_id
    assert captured["slots"] == assessment_service._BLOOM_SLOTS
    assert captured["ability"] == 1.25
    assert captured["excluded_ids"] == excluded_ids
