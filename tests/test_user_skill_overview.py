import uuid

import pytest
from httpx import AsyncClient

from src.models.canonical import ConceptKP
from src.models.learning import LearnerMasteryKP


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

    kp = ConceptKP(
        kp_id="kp_nlp_history",
        name="History of NLP",
        description="NLP foundations",
        track_tags=["nlp"],
        domain_tags=["natural language processing"],
    )
    db_session.add(kp)

    db_session.add(
        LearnerMasteryKP(
            user_id=user_id,
            kp_id=kp.kp_id,
            theta_mu=0.0,
            theta_sigma=1.0,
            mastery_mean_cached=0.42,
            n_items_observed=5,
            updated_by="test",
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
