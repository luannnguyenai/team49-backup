"""
api/app.py
----------
Unified FastAPI application combining:
- Original Lecture Q&A routes (sync)
- New Auth & Learning routes (async)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.store import get_db, Lecture, Chapter, TranscriptLine, QAHistory, init_db
from src.services.llm_service import get_context_and_stream_gemini
from src.database import engine as async_engine
from src.routers.auth import auth_router, users_router
from src.routers.assessment import assessment_router
from src.routers.content import content_router
from src.routers.history import history_router
from src.routers.learning_path import learning_path_router
from src.routers.module_test import module_test_router
from src.routers.quiz import quiz_router
from src.config import settings


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create sync tables for lectures (backward compat)
    init_db()
    yield
    # Shutdown: dispose async engine
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data to serve videos
app.mount("/data", StaticFiles(directory="data"), name="data")
# Mount static files for UI
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")


# ---------------------------------------------------------------------------
# Include routers (new auth/user routes)
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(content_router)
app.include_router(assessment_router)
app.include_router(history_router)
app.include_router(learning_path_router)
app.include_router(module_test_router)
app.include_router(quiz_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["ops"])
async def health_check():
    return {"status": "ok", "app": settings.app_name}


# ---------------------------------------------------------------------------
# Static HTML UI (original)
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    return FileResponse("src/api/static/index.html")


# ---------------------------------------------------------------------------
# Original Lecture Q&A routes
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    lecture_id: str
    current_timestamp: float
    question: str
    image_base64: str = None


@app.get("/api/lectures", tags=["Lectures"])
def list_lectures(db: Session = Depends(get_db)):
    return db.query(Lecture).all()


@app.get("/api/lectures/{lecture_id}/toc", tags=["Lectures"])
def get_toc(lecture_id: str, db: Session = Depends(get_db)):
    chapters = db.query(Chapter).filter(Chapter.lecture_id == lecture_id).order_by(Chapter.start_time).all()
    if not chapters:
        raise HTTPException(status_code=404, detail="ToC not found")
    return chapters


@app.post("/api/lectures/ask", tags=["Lectures"])
def ask_question(req: AskRequest, db: Session = Depends(get_db)):
    try:
        lecture = db.query(Lecture).filter(Lecture.id == req.lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found")

        generator = get_context_and_stream_gemini(
            req.lecture_id,
            req.current_timestamp,
            req.question,
            image_base64=req.image_base64
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lectures/qa-history", tags=["Lectures"])
def get_qa_history(db: Session = Depends(get_db)):
    return db.query(QAHistory).order_by(QAHistory.created_at.desc()).limit(50).all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
