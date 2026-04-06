import json
import os
import re
from sqlalchemy.orm import Session
from src.models.store import Lecture, Chapter, TranscriptLine, SessionLocal, init_db

def parse_toc_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def time_to_seconds(time_str):
    # Support HH:MM:SS
    parts = time_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

def parse_transcript_text(file_path):
    # Expecting format: [HH:MM:SS] Text
    lines_data = []
    if not os.path.exists(file_path):
        return lines_data
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().splitlines()
        
    for line in content:
        match = re.match(r'\[(\d{1,2}:\d{2}:\d{2})\] (.*)', line)
        if match:
            t_str, text = match.groups()
            sec = time_to_seconds(t_str)
            lines_data.append({
                "start_time": float(sec),
                "end_time": float(sec + 5), # Approximate end time per line
                "content": text
            })
    return lines_data

def ingest_lecture(lecture_id, toc_path, transcript_paths, video_filename=None):
    db = SessionLocal()
    init_db()
    
    # Parse ToC
    toc_data = parse_toc_file(toc_path)
    
    # Create or update Lecture
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    video_path = os.path.join("data", video_filename) if video_filename else None
    
    if not lecture:
        lecture = Lecture(
            id=lecture_id, 
            title=toc_data.get("lecture_title", lecture_id),
            video_url=video_path
        )
        db.add(lecture)
    else:
        lecture.title = toc_data.get("lecture_title", lecture_id)
        lecture.video_url = video_path
    
    # Clear existing chapters/lines for re-ingestion
    db.query(Chapter).filter(Chapter.lecture_id == lecture_id).delete()
    db.query(TranscriptLine).filter(TranscriptLine.lecture_id == lecture_id).delete()
    
    # Add Chapters
    for item in toc_data.get("toc", []):
        chapter = Chapter(
            lecture_id=lecture_id,
            title=item["title"],
            summary=item["summary"],
            start_time=float(time_to_seconds(item["start_time"])),
            end_time=float(time_to_seconds(item["end_time"]))
        )
        db.add(chapter)
        
    # Add Transcript Lines
    for t_path in transcript_paths:
        lines = parse_transcript_text(t_path)
        for l in lines:
            line = TranscriptLine(
                lecture_id=lecture_id,
                start_time=l["start_time"],
                end_time=l["end_time"],
                content=l["content"]
            )
            db.add(line)
            
    db.commit()
    db.close()
    print(f"Successfully ingested lecture: {lecture_id}")

if __name__ == "__main__":
    # Ingest Lecture 1
    ingest_lecture(
        "lecture-1", 
        "data/ToC-summary-lecture-1.txt", 
        ["data/splits/Lecture1_Part1.txt", "data/splits/Lecture1_Part2.txt"],
        video_filename="Stanford-CS224N-NLP-with-Deep-Learning-S_Media_DzpHeXVSC5I_001_1080p.mp4"
    )
    # Ingest Lecture 2
    ingest_lecture(
        "lecture-2", 
        "data/ToC-summary-lecture-2.txt", 
        ["data/splits/Lecture2_Part1.txt", "data/splits/Lecture2_Part2.txt"],
        video_filename="Stanford-CS224N-NLP-with-Deep-Learning-S_Media_nBor4jfWetQ_001_1080p.mp4"
    )
