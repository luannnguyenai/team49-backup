"""
routers/assessment.py
---------------------
Assessment Engine API:

    POST  /api/assessment/start                 Start a new assessment session
    POST  /api/assessment/{session_id}/submit   Submit answers + receive results
    GET   /api/assessment/{session_id}/results  Retrieve results for a completed session
    GET   /api/assessment/results               Query-param alias for results
    PATCH /api/assessment/topic-decision        Override placement decision for a unit

Deprecated (308 redirects):
    POST  /api/placement-assessment/start       → /api/assessment/start
    POST  /api/placement-assessment/submit      → /api/assessment/{session_id}/submit
    GET   /api/placement-assessment/results     → /api/assessment/results
    PATCH /api/placement-assessment/topic-decision → /api/assessment/topic-decision

All endpoints require a valid Bearer token (authenticated user).
"""

import uuid

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.assessment import (
    AssessmentResultResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentSubmitRequest,
    TopicDecisionResult,
    TopicDecisionUpdateRequest,
)
from src.services.assessment_service import (
    get_assessment_results,
    start_assessment,
    submit_assessment,
    update_topic_decision,
)

assessment_router = APIRouter(prefix="/api/assessment", tags=["Assessment"])


# ---------------------------------------------------------------------------
# POST /api/assessment/start
# ---------------------------------------------------------------------------


@assessment_router.post(
    "/start",
    response_model=AssessmentStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new assessment session for the given learning units",
    description=(
        "Selects questions per learning unit (1 remember · 2 understand/apply · 2 analyze), "
        "excluding questions the user has previously answered. "
        "Returns the session ID and question list — **correct_answer is never included**."
    ),
)
async def api_start_assessment(
    body: AssessmentStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssessmentStartResponse:
    return await start_assessment(
        db,
        user.id,
        body.learning_unit_ids,
        canonical_unit_ids=body.canonical_unit_ids,
        phase=body.phase,
        assessment_depth=body.assessment_depth,
    )


# ---------------------------------------------------------------------------
# POST /api/assessment/{session_id}/submit
# ---------------------------------------------------------------------------


@assessment_router.post(
    "/{session_id}/submit",
    response_model=AssessmentResultResponse,
    summary="Submit answers and receive scored results with mastery evaluation",
    description=(
        "Grades every answer, persists Interactions, computes bloom-weighted mastery "
        "scores per learning unit, updates canonical mastery state, and returns a full breakdown "
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


# ---------------------------------------------------------------------------
# GET /api/assessment/results  (query-param alias)
# ---------------------------------------------------------------------------


@assessment_router.get(
    "/results",
    response_model=AssessmentResultResponse,
    summary="Retrieve results by session_id query param (alias)",
)
async def api_get_assessment_results_by_query(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> AssessmentResultResponse:
    return await get_assessment_results(db, user.id, session_id)


# ---------------------------------------------------------------------------
# PATCH /api/assessment/topic-decision
# ---------------------------------------------------------------------------


@assessment_router.patch(
    "/topic-decision",
    response_model=TopicDecisionResult,
    summary="Override the placement decision for a topic unit",
)
async def api_update_topic_decision(
    body: TopicDecisionUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> TopicDecisionResult:
    result = await update_topic_decision(db, user.id, body.topic_unit_id, body.user_choice)
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Deprecated 308 redirects: /api/placement-assessment/* → /api/assessment/*
# ---------------------------------------------------------------------------

_deprecated_router = APIRouter(prefix="/api/placement-assessment", tags=["Assessment (deprecated)"])


@_deprecated_router.post("/start")
async def _redirect_start() -> RedirectResponse:
    return RedirectResponse(url="/api/assessment/start", status_code=308)


@_deprecated_router.post("/submit")
async def _redirect_submit() -> RedirectResponse:
    return RedirectResponse(url="/api/assessment/submit", status_code=308)


@_deprecated_router.get("/results")
async def _redirect_results(request: Request) -> RedirectResponse:
    qs = request.url.query
    target = "/api/assessment/results" + (f"?{qs}" if qs else "")
    return RedirectResponse(url=target, status_code=308)


@_deprecated_router.patch("/topic-decision")
async def _redirect_topic_decision() -> RedirectResponse:
    return RedirectResponse(url="/api/assessment/topic-decision", status_code=308)
