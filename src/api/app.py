from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.models.store import get_db, Lecture, Chapter, TranscriptLine, QAHistory, LearningProgress, init_db
from src.services.llm_service import get_context_and_stream_langgraph
from src.routers import auth as auth_router
from src.routers import users as users_router

# Initialize database tables on startup
init_db()

app = FastAPI(title="Lecture Q&A Platform API")

# Auth & user routes
app.include_router(auth_router.router)
app.include_router(users_router.router)

# Mount data to serve videos
app.mount("/data", StaticFiles(directory="data"), name="data")
# Mount static files for UI
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse("src/api/static/index.html")

from typing import Optional

class AskRequest(BaseModel):
    lecture_id: str
    current_timestamp: float
    question: str
    image_base64: Optional[str] = None

@app.get("/api/lectures")
def list_lectures(db: Session = Depends(get_db)):
    return db.query(Lecture).all()

@app.get("/api/lectures/{lecture_id}/toc")
def get_toc(lecture_id: str, db: Session = Depends(get_db)):
    chapters = db.query(Chapter).filter(Chapter.lecture_id == lecture_id).order_by(Chapter.start_time).all()
    if not chapters:
        raise HTTPException(status_code=404, detail="ToC not found")
    return chapters

@app.post("/api/lectures/ask")
def ask_question(req: AskRequest, db: Session = Depends(get_db)):
    try:
        # Check if lecture exists
        lecture = db.query(Lecture).filter(Lecture.id == req.lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail="Lecture not found")
            
        generator = get_context_and_stream_langgraph(
            req.lecture_id, 
            req.current_timestamp, 
            req.question,
            image_base64=req.image_base64
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    return db.query(QAHistory).order_by(QAHistory.created_at.desc()).limit(50).all()

class RateRequest(BaseModel):
    rating: int  # 1 = 👍, -1 = 👎

@app.post("/api/history/{qa_id}/rate")
def rate_answer(qa_id: int, req: RateRequest, db: Session = Depends(get_db)):
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")
    qa = db.query(QAHistory).filter(QAHistory.id == qa_id).first()
    if not qa:
        raise HTTPException(status_code=404, detail="QA entry not found")
    qa.rating = req.rating
    db.commit()
    return {"status": "ok", "qa_id": qa_id, "rating": req.rating}

# --- Learning Progress Tracking ---

class ProgressRequest(BaseModel):
    session_id: str
    lecture_id: str
    last_timestamp: float

@app.post("/api/progress")
def save_progress(req: ProgressRequest, db: Session = Depends(get_db)):
    """Upsert learning progress for a session + lecture pair."""
    progress = db.query(LearningProgress).filter(
        LearningProgress.session_id == req.session_id,
        LearningProgress.lecture_id == req.lecture_id,
    ).first()
    if progress:
        progress.last_timestamp = req.last_timestamp
    else:
        progress = LearningProgress(
            session_id=req.session_id,
            lecture_id=req.lecture_id,
            last_timestamp=req.last_timestamp,
        )
        db.add(progress)
    db.commit()
    return {"status": "ok"}

@app.get("/api/progress/{session_id}")
def get_progress(session_id: str, db: Session = Depends(get_db)):
    """Get all learning progress entries for a session."""
    rows = db.query(LearningProgress).filter(
        LearningProgress.session_id == session_id
    ).all()
    return {row.lecture_id: row.last_timestamp for row in rows}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

