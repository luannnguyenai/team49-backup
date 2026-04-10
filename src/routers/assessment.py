"""
routers/assessment.py
---------------------
Assessment Engine API:

    POST  /api/assessment/start                 Start a new assessment session
    POST  /api/assessment/{session_id}/submit   Submit answers + receive results
    GET   /api/assessment/{session_id}/results  Retrieve results for a completed session

All endpoints require a valid Bearer token (authenticated user).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.assessment import (
    AssessmentResultResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentSubmitRequest,
)
from src.services.assessment_service import (
    get_assessment_results,
    start_assessment,
    submit_assessment,
)

assessment_router = APIRouter(prefix="/api/assessment", tags=["Assessment"])


# ---------------------------------------------------------------------------
# POST /api/assessment/start
# ---------------------------------------------------------------------------

@assessment_router.post(
    "/start",
    response_model=AssessmentStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new assessment session for the given topics",
    description=(
        "Selects 5 questions per topic (1 remember · 2 understand/apply · 2 analyze), "
        "excluding questions the user has previously answered. "
        "Returns the session ID and question list — **correct_answer is never included**."
    ),
)
async def api_start_assessment(
    body: AssessmentStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssessmentStartResponse:
    return await start_assessment(db, user.id, body.topic_ids)


# ---------------------------------------------------------------------------
# POST /api/assessment/{session_id}/submit
# ---------------------------------------------------------------------------

@assessment_router.post(
    "/{session_id}/submit",
    response_model=AssessmentResultResponse,
    summary="Submit answers and receive scored results with mastery evaluation",
    description=(
        "Grades every answer, persists Interactions, computes bloom-weighted mastery "
        "scores per topic, upserts MasteryScore records, and returns a full breakdown "
        "including weak KCs and detected misconceptions."
    ),
)
async def api_submit_assessment(
    session_id: uuid.UUID,
    body: AssessmentSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssessmentResultResponse:
    return await submit_assessment(db, user.id, session_id, body.answers)


# ---------------------------------------------------------------------------
# GET /api/assessment/{session_id}/results
# ---------------------------------------------------------------------------

@assessment_router.get(
    "/{session_id}/results",
    response_model=AssessmentResultResponse,
    summary="Retrieve stored results for a completed assessment session",
)
async def api_get_assessment_results(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssessmentResultResponse:
    return await get_assessment_results(db, user.id, session_id)
