import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "../../app.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    title = Column(String)
    summary = Column(Text)
    start_time = Column(Float)  # seconds
    end_time = Column(Float)    # seconds
    
    lecture = relationship("Lecture", back_populates="chapters")

class TranscriptLine(Base):
    __tablename__ = "transcript_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    start_time = Column(Float, index=True)
    end_time = Column(Float)
    content = Column(Text)
    
    lecture = relationship("Lecture", back_populates="transcript_lines")

class QAHistory(Base):
    __tablename__ = "qa_history"
    
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(String, ForeignKey("lectures.id"))
    question = Column(Text)
    answer = Column(Text)
    thoughts = Column(Text, nullable=True) # Quá trình suy nghĩ sâu
    current_timestamp = Column(Float)
    image_base64 = Column(Text, nullable=True) # Ảnh đã chụp lúc đó
    rating = Column(Integer, nullable=True)  # 1 = 👍, -1 = 👎, null = chưa đánh giá
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
