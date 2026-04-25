# src/routers/placement_assessment.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.exceptions import NotFoundError
from src.models.user import User
from src.repositories.placement_assessment_repo import PlacementAssessmentRepository
from src.schemas.placement_assessment import (
    PlacementResultsResponse,
    PlacementStartRequest,
    PlacementStartResponse,
    PlacementSubmitRequest,
    PlacementSubmitResponse,
    TopicDecision,
    TopicUserChoiceRequest,
)
from src.services.placement_assessment_service import (
    start_placement_assessment,
    submit_placement_assessment,
)

placement_assessment_router = APIRouter(
    prefix="/api/placement-assessment",
    tags=["placement-assessment"],
)


@placement_assessment_router.post("/start", response_model=PlacementStartResponse)
async def start_placement(
    body: PlacementStartRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementStartResponse:
    return await start_placement_assessment(
        db,
        user_id=current_user.id,
        topic_unit_ids=body.topic_unit_ids,
    )


@placement_assessment_router.post("/submit", response_model=PlacementSubmitResponse)
async def submit_placement(
    body: PlacementSubmitRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementSubmitResponse:
    result = await submit_placement_assessment(
        db,
        user_id=current_user.id,
        session_id=body.session_id,
        answers=body.answers,
    )
    await db.commit()
    return result


@placement_assessment_router.get("/results", response_model=PlacementResultsResponse)
async def get_placement_results(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> PlacementResultsResponse:
    repo = PlacementAssessmentRepository(db)
    rows = await repo.get_by_user_id(current_user.id)
    decisions = [
        TopicDecision(
            topic_unit_id=row.topic_unit_id,
            score_pct=float(row.score_pct),
            decision=row.decision,
            user_choice=row.user_choice,
        )
        for row in rows
    ]
    return PlacementResultsResponse(results=decisions, has_placement=len(decisions) > 0)


@placement_assessment_router.patch("/topic-decision", response_model=TopicDecision)
async def set_topic_user_choice(
    body: TopicUserChoiceRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
) -> TopicDecision:
    repo = PlacementAssessmentRepository(db)
    row = await repo.get_by_user_and_unit(current_user.id, body.topic_unit_id)
    if row is None or row.decision != "review":
        raise NotFoundError("No reviewable placement result for this topic.")
    row.user_choice = body.user_choice
    db.add(row)
    await db.commit()
    return TopicDecision(
        topic_unit_id=row.topic_unit_id,
        score_pct=float(row.score_pct),
        decision=row.decision,
        user_choice=row.user_choice,
    )
