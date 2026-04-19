"""Tests for read-oriented KG router endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.kg.schemas import (
    KCNode,
    LearningPath,
    PathTopic,
    PathWeek,
    RankedCandidate,
    TopicContext,
    TopicNode,
)
import src.kg.router as kg_router


class FakeReadService:
    async def get_topic_context(self, topic_slug: str, hops: int = 2) -> TopicContext:
        if topic_slug == "missing":
            raise KeyError(topic_slug)
        return TopicContext(
            topic=TopicNode(
                slug=topic_slug,
                module_slug="mini_cv",
                name="CV Attention",
                prerequisite_topic_slugs=(),
                estimated_hours_beginner=10.0,
                estimated_hours_review=4.0,
            ),
            prereqs=(),
            kcs=(
                KCNode(
                    slug="KC-CV-self-attention",
                    topic_slug=topic_slug,
                    module_slug="mini_cv",
                    name="Self-Attention",
                ),
            ),
            sibling_kcs=(),
            transfers=(),
        )

    async def build_path(
        self,
        user_id: uuid.UUID,
        target_topics: list[str],
        hours_per_week: float,
    ) -> LearningPath:
        return LearningPath(
            weeks=(
                PathWeek(
                    week_number=1,
                    topics=(
                        PathTopic(
                            slug=target_topics[0],
                            mode="learn",
                            hours=4.0,
                            mastery=0.0,
                            shortcuts=(),
                        ),
                    ),
                    total_hours=4.0,
                    shortcuts=(),
                ),
            )
        )

    async def rank_next(
        self,
        user_id: uuid.UUID,
        candidate_limit: int = 20,
    ) -> list[RankedCandidate]:
        return [
            RankedCandidate(
                topic_slug="cv_attention_transformers",
                score=0.9,
                mastery_gap=0.8,
                prereq_ready=1.0,
                transfer_boost=0.7,
                goal_distance=0.0,
                freshness_penalty=0.0,
            )
        ]


@pytest.mark.asyncio
async def test_kg_read_endpoints_happy_path() -> None:
    app.dependency_overrides[kg_router.get_kg_service] = lambda: FakeReadService()
    user_id = str(uuid.uuid4())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            context_response = await client.get("/kg/topic/cv_attention_transformers/context")
            path_response = await client.post(
                "/kg/path",
                json={
                    "user_id": user_id,
                    "target_topics": ["cv_attention_transformers"],
                    "hours_per_week": 5.0,
                },
            )
            recommend_response = await client.get(f"/kg/recommend/next?user_id={user_id}")
    finally:
        app.dependency_overrides.clear()

    assert context_response.status_code == 200
    assert context_response.json()["topic"]["slug"] == "cv_attention_transformers"
    assert path_response.status_code == 200
    assert path_response.json()["weeks"][0]["topics"][0]["slug"] == "cv_attention_transformers"
    assert recommend_response.status_code == 200
    assert recommend_response.json()[0]["topic_slug"] == "cv_attention_transformers"


@pytest.mark.asyncio
async def test_kg_topic_context_returns_404_when_slug_missing() -> None:
    app.dependency_overrides[kg_router.get_kg_service] = lambda: FakeReadService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/kg/topic/missing/context")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
