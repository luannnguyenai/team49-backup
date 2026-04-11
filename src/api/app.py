from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.models.store import get_db, Lecture, Chapter, TranscriptLine, QAHistory, init_db
from src.services.llm_service import get_context_and_stream_langgraph

# Initialize database tables on startup
init_db()

app = FastAPI(title="Lecture Q&A Platform API")

# Mount data to serve videos
app.mount("/data", StaticFiles(directory="data"), name="data")
# Mount static files for UI
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse("src/api/static/index.html")

class AskRequest(BaseModel):
    lecture_id: str
    current_timestamp: float
    question: str
    image_base64: str = None

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
