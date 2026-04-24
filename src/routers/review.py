from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.review import ReviewStartRequest, ReviewStartResponse
from src.services.review_service import start_review_session

review_router = APIRouter(prefix="/api/review", tags=["Review"])


@review_router.post(
    "/start",
    response_model=ReviewStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def api_start_review(
    body: ReviewStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> ReviewStartResponse:
    return await start_review_session(
        db,
        user_id=user.id,
        learning_unit_ids=body.learning_unit_ids,
        count=body.count,
    )
