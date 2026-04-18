import uuid

import pytest
from httpx import AsyncClient

from src.models.content import Module, Topic
from src.models.learning import MasteryLevel, MasteryScore


@pytest.mark.asyncio
async def test_user_skill_overview_returns_real_mastery_scores(
    db_client: AsyncClient,
    db_session,
):
    reg = await db_client.post(
        "/api/auth/register",
        json={
            "email": "skill-user@example.com",
            "password": "SecurePass123!",
            "full_name": "Skill User",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]

    me = await db_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = uuid.UUID(me.json()["id"])

    module = Module(
        name="CS224N: Natural Language Processing with Deep Learning",
        description="NLP foundations",
        order_index=1,
        prerequisite_module_ids=[],
    )
    db_session.add(module)
    await db_session.flush()

    topic = Topic(
        module_id=module.id,
        name="History of NLP",
        description="Intro topic",
        order_index=1,
        prerequisite_topic_ids=[],
    )
    db_session.add(topic)
    await db_session.flush()

    db_session.add(
        MasteryScore(
            user_id=user_id,
            topic_id=topic.id,
            kc_id=None,
            mastery_probability=0.42,
            mastery_level=MasteryLevel.developing,
            evidence_count=5,
        )
    )
    await db_session.flush()

    response = await db_client.get(
        "/api/users/me/skills",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["skills"]) == 5

    skill_map = {skill["label"]: skill for skill in data["skills"]}
    assert skill_map["NLP"]["value"] == 42.0
    assert skill_map["NLP"]["level"] == "developing"
    assert skill_map["Computer Vision"]["value"] == 0.0
    assert skill_map["Computer Vision"]["level"] == "not_started"
