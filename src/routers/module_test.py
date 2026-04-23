"""
routers/module_test.py
----------------------
Module Test System API.

Endpoints
---------
POST  /api/module-test/start                  Start a new module test session
POST  /api/module-test/{session_id}/submit    Submit all answers; receive graded results
GET   /api/module-test/{session_id}/results   Retrieve results for a past session

All endpoints require a valid Bearer token.

Business rules (enforced in the service layer)
-----------------------------------------------
* start    : user must have ≥ 1 completed quiz session for EVERY topic in the
             module before the test may begin.
* submit   : 2 Easy + 1 Medium + 2 Hard questions per topic (5 total).
             PASS  = total_score_percent ≥ 70 %
               → mastery updated to max(current, test_score) per topic
               → next_module returned in response
             FAIL  = total_score_percent < 70 %
               → weak topics (score < 60 %) added to learning_path as "remediate"
* results  : read-only re-computation from stored interactions — no DB mutations.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.module_test import (
    ModuleTestResultResponse,
    ModuleTestStartRequest,
    ModuleTestStartResponse,
    ModuleTestSubmitRequest,
)
from src.services.module_test_service import (
    get_module_test_results,
    start_module_test,
    submit_module_test,
)

module_test_router = APIRouter(prefix="/api/module-test", tags=["Module Test"])


# ---------------------------------------------------------------------------
# POST /api/module-test/start
# ---------------------------------------------------------------------------


@module_test_router.post(
    "/start",
    response_model=ModuleTestStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new module test session",
    description=(
        "Validates that the user has completed at least one quiz for every topic "
        "in the module. Selects 5 questions per topic (2 Easy · 1 Medium · 2 Hard) "
        "filtered by usage_context='module_test', applying tier-based prioritisation "
        "(never-answered → previously-wrong → always-correct)."
    ),
)
async def api_start_module_test(
    body: ModuleTestStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ModuleTestStartResponse:
    return await start_module_test(db, user.id, body.module_id)


# ---------------------------------------------------------------------------
# POST /api/module-test/{session_id}/submit
# ---------------------------------------------------------------------------


@module_test_router.post(
    "/{session_id}/submit",
    response_model=ModuleTestResultResponse,
    summary="Submit all answers and receive graded results",
    description=(
        "Grades the full test in one shot. "
        "PASS (≥ 70 %): updates mastery per topic to max(current, test_score) "
        "and returns the next module. "
        "FAIL (< 70 %): records legacy remediation entries for each weak topic "
        "(score < 60 %) and returns targeted review suggestions."
    ),
)
async def api_submit_module_test(
    session_id: uuid.UUID,
    body: ModuleTestSubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ModuleTestResultResponse:
    return await submit_module_test(db, user.id, session_id, body)


# ---------------------------------------------------------------------------
# GET /api/module-test/{session_id}/results
# ---------------------------------------------------------------------------


@module_test_router.get(
    "/{session_id}/results",
    response_model=ModuleTestResultResponse,
    summary="Retrieve results for a completed module test session",
    description=(
        "Re-computes and returns the graded result from stored interactions. "
        "Read-only: no mastery updates or learning-path mutations are applied. "
        "Returns 409 if the session has not been submitted yet."
    ),
)
async def api_get_module_test_results(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ModuleTestResultResponse:
    return await get_module_test_results(db, user.id, session_id)
