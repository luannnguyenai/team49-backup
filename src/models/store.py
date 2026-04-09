"""
models/store.py
---------------
Original A20-App-049 lecture models, now using the shared Base from base.py.
Provides both sync (get_db) and async (get_async_db) database access.

Models: Lecture, Chapter, TranscriptLine, QAHistory
"""

from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import sessionmaker, relationship

from src.models.base import Base
from src.config import settings

# ---------------------------------------------------------------------------
# Sync engine for legacy lecture operations (ingestion, llm_service)
# Converts asyncpg URL → psycopg2 URL for synchronous SQLAlchemy usage.
# ---------------------------------------------------------------------------
_SYNC_DATABASE_URL = (
    settings.database_url
    .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    .replace("postgresql://", "postgresql+psycopg2://")
)

engine = create_engine(_SYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapters = relationship("Chapter", back_populates="lecture", cascade="all, delete-orphan")
    transcript_lines = relationship("TranscriptLine", back_populates="lecture", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    title = Column(String)
    summary = Column(Text)
    start_time = Column(Float)  # seconds
    end_time = Column(Float)    # seconds

    lecture = relationship("Lecture", back_populates="chapters")


class TranscriptLine(Base):
    __tablename__ = "transcript_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    start_time = Column(Float, index=True)
    end_time = Column(Float)
    content = Column(Text)

    lecture = relationship("Lecture", back_populates="transcript_lines")


class QAHistory(Base):
    __tablename__ = "qa_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    question = Column(Text)
    answer = Column(Text)
    thoughts = Column(Text, nullable=True)
    current_timestamp = Column(Float)
    image_base64 = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables (sync, for lecture models)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Sync database session dependency for FastAPI (legacy lecture routes)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
