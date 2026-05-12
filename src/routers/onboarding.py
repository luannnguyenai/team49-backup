"""
routers/onboarding.py
---------------------
Onboarding flow endpoints:
  POST /api/users/me/onboarding/goals
  GET  /api/onboarding/topics
  POST /api/users/me/onboarding/known-topics
  POST /api/users/me/onboarding/experience-level
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.onboarding import (
    ExperienceLevelRequest,
    ExperienceLevelResponse,
    GoalsRequest,
    GoalsResponse,
    KnownTopicsRequest,
    KnownTopicsResponse,
    PriorAnalysisRequest,
    PriorAnalysisResponse,
    TopicsResponse,
)
from src.services.onboarding_service import (
    analyze_prior_profile,
    get_topics_tree,
    save_experience_level,
    save_known_topics,
    save_user_goals,
)

onboarding_router = APIRouter(tags=["onboarding"])


@onboarding_router.post(
    "/api/users/me/onboarding/goals",
    response_model=GoalsResponse,
)
async def set_onboarding_goals(
    body: GoalsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> GoalsResponse:
    return await save_user_goals(db, user_id=current_user.id, goal_ids=body.goal_ids)


@onboarding_router.get(
    "/api/onboarding/topics",
    response_model=TopicsResponse,
)
async def get_onboarding_topics(
    goal: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_async_db),
) -> TopicsResponse:
    return await get_topics_tree(db, goal_ids=goal)


@onboarding_router.post(
    "/api/users/me/onboarding/known-topics",
    response_model=KnownTopicsResponse,
)
async def set_known_topics(
    body: KnownTopicsRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> KnownTopicsResponse:
    return await save_known_topics(db, user_id=current_user.id, topic_unit_ids=body.topic_unit_ids)


@onboarding_router.post(
    "/api/users/me/onboarding/experience-level",
    response_model=ExperienceLevelResponse,
)
async def set_experience_level(
    body: ExperienceLevelRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> ExperienceLevelResponse:
    return await save_experience_level(db, user_id=current_user.id, level=body.level)


@onboarding_router.post(
    "/api/onboarding/prior-analysis",
    response_model=PriorAnalysisResponse,
)
async def analyze_prior_knowledge(
    body: PriorAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> PriorAnalysisResponse:
    _ = current_user
    return await analyze_prior_profile(body)
