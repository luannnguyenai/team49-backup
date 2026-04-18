"""
api/app.py
----------
Unified FastAPI application:
- Lecture Q&A routes (async, using AsyncSession)
- Auth & Learning routes (async)
"""

import asyncio
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_factory, engine as async_engine, get_async_db
from src.exception_handlers import domain_exception_handler
from src.exceptions import DomainError
from src.redis_client import connect_redis, disconnect_redis
from src.models.store import Lecture, Chapter, QAHistory, LearningProgress
from src.services.llm_service import get_context_and_stream_langgraph
from src.routers.auth import auth_router, users_router
from src.routers.assessment import assessment_router
from src.routers.content import content_router
from src.routers.courses import courses_router
from src.routers.history import history_router
from src.routers.learning_path import learning_path_router
from src.routers.module_test import module_test_router
from src.routers.quiz import quiz_router
from src.routers.test_support import test_support_router
from src.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await connect_redis()
    except Exception as exc:
        logger.warning("Redis unavailable during startup; continuing without shared cache: %s", exc)

    try:
        yield
    finally:
        await disconnect_redis()
        await async_engine.dispose()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    description="AI-powered adaptive learning platform with Lecture Q&A",
    version="0.2.0",
    lifespan=lifespan,
)

# Exception handler — maps DomainError subclasses to HTTP status codes
app.add_exception_handler(DomainError, domain_exception_handler)

# CORS — explicit origins, not wildcard (wildcard + credentials is rejected by browsers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Static mounts
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(content_router)
app.include_router(courses_router)
app.include_router(assessment_router)
app.include_router(history_router)
app.include_router(learning_path_router)
app.include_router(module_test_router)
app.include_router(quiz_router)
app.include_router(test_support_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
async def health_check():
    return {"status": "ok", "app": settings.app_name}


# ---------------------------------------------------------------------------
# API landing
# ---------------------------------------------------------------------------
@app.get("/", tags=["ops"])
async def read_root():
    return {
        "app": settings.app_name,
        "surface": "backend_api",
        "message": "This server exposes the FastAPI backend only. Open the Next.js frontend on port 3000 for the course UI.",
        "frontend_dev_url": "http://127.0.0.1:3000",
        "health_url": "/health",
        "openapi_url": "/openapi.json",
        "docs_url": "/docs",
        "legacy_static_ui": "/static/index.html",
    }


# ---------------------------------------------------------------------------
# Lecture Q&A routes (async — uses get_async_db)
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    lecture_id: str
    current_timestamp: float
    question: str
    image_base64: str | None = None


def _ensure_lecture_exists(lecture_id: str, db: object | None = None) -> None:
    if db is not None:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found")
        return

    async def _load_lecture_id() -> str | None:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Lecture.id).where(Lecture.id == lecture_id).limit(1)
            )
            return result.scalar_one_or_none()

    lecture = asyncio.run(_load_lecture_id())
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")


@app.get("/api/lectures", tags=["Lectures"])
async def list_lectures(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Lecture))
    return result.scalars().all()


@app.get("/api/lectures/{lecture_id}/toc", tags=["Lectures"])
async def get_toc(lecture_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(Chapter)
        .where(Chapter.lecture_id == lecture_id)
        .order_by(Chapter.start_time)
    )
    chapters = result.scalars().all()
    if not chapters:
        raise HTTPException(status_code=404, detail="ToC not found")
    return chapters


@app.post("/api/lectures/ask", tags=["Lectures"])
def ask_question(req: AskRequest, db: object | None = None):
    """
    Sync route — runs in FastAPI threadpool.
    llm_service uses asyncio.run() internally for DB access.
    LangGraph streaming remains sync (no async streaming support yet).
    """
    try:
        _ensure_lecture_exists(req.lecture_id, db=db)
        generator = get_context_and_stream_langgraph(
            req.lecture_id,
            req.current_timestamp,
            req.question,
            image_base64=req.image_base64,
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lectures/qa-history", tags=["Lectures"])
async def get_qa_history(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(QAHistory).order_by(QAHistory.created_at.desc()).limit(50)
    )
    return result.scalars().all()


class RateRequest(BaseModel):
    rating: int  # 1 = 👍, -1 = 👎


@app.post("/api/history/{qa_id}/rate")
async def rate_answer(qa_id: int, req: RateRequest, db: AsyncSession = Depends(get_async_db)):
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")
    result = await db.execute(select(QAHistory).where(QAHistory.id == qa_id))
    qa = result.scalar_one_or_none()
    if not qa:
        raise HTTPException(status_code=404, detail="QA entry not found")
    qa.rating = req.rating
    return {"status": "ok", "qa_id": qa_id, "rating": req.rating}


# ---------------------------------------------------------------------------
# Learning Progress routes (async)
# ---------------------------------------------------------------------------

class ProgressRequest(BaseModel):
    session_id: str
    lecture_id: str
    last_timestamp: float


_WATCHED_THRESHOLD = 0.8


@app.post("/api/progress")
async def save_progress(req: ProgressRequest, db: AsyncSession = Depends(get_async_db)):
    """Upsert learning progress. Auto-upgrades state to 'watched' at 80%."""
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.session_id == req.session_id,
            LearningProgress.lecture_id == req.lecture_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LearningProgress(
            session_id=req.session_id,
            lecture_id=req.lecture_id,
            last_timestamp=req.last_timestamp,
            checkpoint_state="unwatched",
        )
        db.add(progress)
    else:
        progress.last_timestamp = req.last_timestamp

    if progress.checkpoint_state == "unwatched":
        lec_result = await db.execute(select(Lecture).where(Lecture.id == req.lecture_id))
        lecture = lec_result.scalar_one_or_none()
        if lecture and lecture.duration and lecture.duration > 0:
            if req.last_timestamp / lecture.duration >= _WATCHED_THRESHOLD:
                progress.checkpoint_state = "watched"

    return {"status": "ok", "checkpoint_state": progress.checkpoint_state}


@app.post("/api/progress/{session_id}/{lecture_id}/quiz-complete")
async def mark_quiz_complete(
    session_id: str, lecture_id: str, db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.session_id == session_id,
            LearningProgress.lecture_id == lecture_id,
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = LearningProgress(
            session_id=session_id,
            lecture_id=lecture_id,
            checkpoint_state="quiz_completed",
        )
        db.add(progress)
    else:
        progress.checkpoint_state = "quiz_completed"

    return {"status": "ok", "checkpoint_state": "quiz_completed"}


@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(LearningProgress).where(LearningProgress.session_id == session_id)
    )
    rows = result.scalars().all()
    return {
        row.lecture_id: {
            "last_timestamp": row.last_timestamp,
            "checkpoint_state": row.checkpoint_state,
        }
        for row in rows
    }
