import os

# 1. Resolve auth.py
os.system("git checkout --ours src/routers/auth.py")

# 2. Resolve config.py
os.system("git checkout --ours src/config.py")
with open("src/config.py", "r") as f:
    text = f.read()

config_add = """    default_model: str = Field(default="gemini-3-flash-preview", description="Default LLM model")
    fast_model: str = Field(default="gemini-2.5-flash", description="Fast model for minor tasks")
    model_provider: str = Field(default="google_genai", description="LLM provider")"""
text = text.replace('    default_model: str = Field(default="gemini-3-flash-preview", description="Default LLM model")', config_add)

config_alias = """DEFAULT_MODEL = settings.default_model
FAST_MODEL = settings.fast_model
MODEL_PROVIDER = settings.model_provider"""
text = text.replace('DEFAULT_MODEL = settings.default_model', config_alias)

with open("src/config.py", "w") as f:
    f.write(text)


# 3. Resolve store.py
os.system("git checkout --ours src/models/store.py")
with open("src/models/store.py", "r") as f:
    text = f.read()

text = text.replace("DateTime\n", "DateTime, UniqueConstraint\n")
text = text.replace("image_base64 = Column(Text, nullable=True)\n    created_at = Column(DateTime, default=datetime.utcnow)", 
"""image_base64 = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)""")

store_add = """

class LearningProgress(Base):
    __tablename__ = "learning_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    lecture_id = Column(String, ForeignKey("lectures.id"), nullable=False)
    last_timestamp = Column(Float, default=0.0)  # seconds into video
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("session_id", "lecture_id", name="uq_session_lecture"),
    )
"""
text = text.replace("def init_db():", store_add + "\ndef init_db():")

with open("src/models/store.py", "w") as f:
    f.write(text)


# 4. Resolve app.py
os.system("git checkout --ours src/api/app.py")
with open("src/api/app.py", "r") as f:
    text = f.read()

text = text.replace("from src.models.store import get_db, Lecture, Chapter, TranscriptLine, QAHistory, init_db",
                   "from src.models.store import get_db, Lecture, Chapter, TranscriptLine, QAHistory, LearningProgress, init_db")
text = text.replace("from src.services.llm_service import get_context_and_stream_gemini",
                   "from src.services.llm_service import get_context_and_stream_langgraph")

text = text.replace("get_context_and_stream_gemini(", "get_context_and_stream_langgraph(")

app_routes = """
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
    \"\"\"Upsert learning progress for a session + lecture pair.\"\"\"
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
    \"\"\"Get all learning progress entries for a session.\"\"\"
    rows = db.query(LearningProgress).filter(
        LearningProgress.session_id == session_id
    ).all()
    return {row.lecture_id: row.last_timestamp for row in rows}

if __name__ == "__main__":
"""
text = text.replace('if __name__ == "__main__":', app_routes)

with open("src/api/app.py", "w") as f:
    f.write(text)

