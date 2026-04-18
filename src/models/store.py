"""
models/store.py
---------------
Original A20-App-049 lecture models, using the shared Base from base.py.
All DB access is async via AsyncSession (get_async_db dependency).

Models: Lecture, Chapter, TranscriptLine, QAHistory, LearningProgress

Important boundary:
- These tables are transitional adapter tables for the legacy CS231n tutor stack.
- They must not replace the canonical course-first product domain in
  `src/models/course.py`.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from src.models.base import Base


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
    context_binding_id = Column(String(255), nullable=True)
    image_base64 = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)




class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    lecture_id = Column(String, ForeignKey("lectures.id"), nullable=False)
    last_timestamp = Column(Float, default=0.0)       # seconds into video
    # "unwatched" | "watched" | "quiz_completed"
    checkpoint_state = Column(String, nullable=False, default="unwatched")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("session_id", "lecture_id", name="uq_session_lecture"),
    )
