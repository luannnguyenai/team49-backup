import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.models.learning import PathAction


@pytest.mark.asyncio
async def test_write_planner_audit_if_enabled_persists_plan_rationale_and_state(monkeypatch):
    from src.services import recommendation_engine

    captured = {"plan": None, "rationales": [], "session": None}

    class FakePlannerAuditRepository:
        def __init__(self, session):
            assert session == "db-session"

        async def create_plan(self, **kwargs):
            captured["plan"] = kwargs
            return SimpleNamespace(id=uuid.uuid4())

        async def add_rationale(self, **kwargs):
            captured["rationales"].append(kwargs)
            return Mock()

        async def upsert_session_state(self, **kwargs):
            captured["session"] = kwargs
            return Mock()

    monkeypatch.setattr(recommendation_engine.settings, "write_planner_audit_enabled", True)
    monkeypatch.setattr(
        recommendation_engine,
        "PlannerAuditRepository",
        FakePlannerAuditRepository,
    )

    topic_1 = SimpleNamespace(id=uuid.uuid4(), name="CNN Basics")
    topic_2 = SimpleNamespace(id=uuid.uuid4(), name="Transformers")
    classified = [
        SimpleNamespace(
            topic=topic_1,
            action=PathAction.deep_practice,
            estimated_hours=2.5,
            order_index=0,
            module_name="Vision",
        ),
        SimpleNamespace(
            topic=topic_2,
            action=PathAction.skip,
            estimated_hours=0.0,
            order_index=1,
            module_name="NLP",
        ),
    ]
    timeline = SimpleNamespace(topic_week_map={topic_1.id: 1, topic_2.id: None})

    await recommendation_engine._write_planner_audit_if_enabled(
        db="db-session",
        user_id=uuid.uuid4(),
        now=SimpleNamespace(isoformat=lambda: "2026-04-23T12:00:00+00:00"),
        classified=classified,
        timeline=timeline,
        mastery_by_topic={topic_1.id: 24.0, topic_2.id: 82.0},
        misconception_topics={topic_1.id},
    )

    assert captured["plan"] is not None
    assert captured["plan"]["trigger"] == "generate_learning_path"
    assert len(captured["plan"]["recommended_path_json"]) == 2
    assert len(captured["rationales"]) == 2
    assert captured["rationales"][0]["reason_code"] == "legacy_topic_deep_practice"
    assert captured["rationales"][1]["reason_code"] == "legacy_topic_skip"
    assert captured["session"]["session_id"] == "learning-path"
    assert captured["session"]["state_json"]["topic_count"] == 2
    assert captured["session"]["state_json"]["skipped_topic_ids"] == [str(topic_2.id)]


@pytest.mark.asyncio
async def test_write_planner_audit_if_enabled_noops_when_flag_disabled(monkeypatch):
    from src.services import recommendation_engine

    class FakePlannerAuditRepository:
        def __init__(self, session):
            raise AssertionError("PlannerAuditRepository should not be used when flag is off")

    monkeypatch.setattr(recommendation_engine.settings, "write_planner_audit_enabled", False)
    monkeypatch.setattr(
        recommendation_engine,
        "PlannerAuditRepository",
        FakePlannerAuditRepository,
    )

    await recommendation_engine._write_planner_audit_if_enabled(
        db="db-session",
        user_id=uuid.uuid4(),
        now=SimpleNamespace(isoformat=lambda: "2026-04-23T12:00:00+00:00"),
        classified=[],
        timeline=SimpleNamespace(topic_week_map={}),
        mastery_by_topic={},
        misconception_topics=set(),
    )
