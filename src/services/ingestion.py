import json
import os
import re

from src.models.store import Chapter, Lecture, SessionLocal, TranscriptLine, init_db


def parse_toc_file(file_path):
    """Parses the new JSON ToC structure."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    return data


def time_to_seconds(time_str):
    """Converts HH:MM:SS or MM:SS to seconds."""
    if not time_str:
        return 0
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return 0
    return 0


def parse_transcript_text(file_path):
    """
    Parses transcripts where timestamps are on their own lines.
    Format:
    00:00:05
    Text content...
    """
    lines_data = []
    if not os.path.exists(file_path):
        return lines_data

    with open(file_path, encoding="utf-8") as f:
        content = f.read().splitlines()

    current_time = None
    current_text = []

    for line in content:
        line = line.strip()
        if not line:
            continue

        # Check if line is a timestamp (HH:MM:SS)
        if re.match(r"^\d{1,2}:\d{2}:\d{2}$", line):
            # If we were collecting text for a previous timestamp, save it
            if current_time is not None and current_text:
                sec = time_to_seconds(current_time)
                lines_data.append({"start_time": float(sec), "content": " ".join(current_text)})
            current_time = line
            current_text = []
        elif current_time is not None:
            # It's text content for the current timestamp
            current_text.append(line)

    # Add the last segment
    if current_time is not None and current_text:
        sec = time_to_seconds(current_time)
        lines_data.append({"start_time": float(sec), "content": " ".join(current_text)})

    # Calculate end times based on the next start time
    for i in range(len(lines_data) - 1):
        lines_data[i]["end_time"] = lines_data[i + 1]["start_time"]
    if lines_data:
        lines_data[-1]["end_time"] = (
            lines_data[-1]["start_time"] + 5.0
        )  # default buffer for last line

    return lines_data


def sanitize_title(title, lecture_id):
    """Standardizes titles to 'Lecture N: Topic' format."""
    # Extract lecture number from ID (lecture-1 -> 1)
    match_id = re.search(r"lecture-(\d+)", lecture_id)
    n = match_id.group(1) if match_id else "?"

    # Remove redundant prefixes
    title = re.sub(
        r"Stanford\s+CS231N?|Deep\s+Learning\s+for\s+Computer\s+Vision|Spring\s+2025",
        "",
        title,
        flags=re.I,
    )
    # Remove "Lecture X:" if already in title to avoid duplication
    title = re.sub(rf"Lecture\s+{n}[:\-]?", "", title, flags=re.I)
    # Clean up symbols and extra spaces
    title = re.sub(r"^[|:\-\s]+", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    return f"Lecture {n}: {title}"


def ingest_lecture(lecture_id, toc_path, transcript_paths, video_rel_path=None):
    """Ingests a lecture using the new JSON ToC and Transcript format."""
    db = SessionLocal()
    init_db()

    # Parse ToC
    toc_data = parse_toc_file(toc_path)
    if not toc_data:
        print(f"Error: ToC file not found at {toc_path}")
        return

    # Standardize Title
    raw_title = toc_data.get("lecture_title", lecture_id)
    clean_title = sanitize_title(raw_title, lecture_id)

    # Create or update Lecture
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()

    if not lecture:
        lecture = Lecture(id=lecture_id, title=clean_title, video_url=video_rel_path)
        db.add(lecture)
    else:
        lecture.title = clean_title
        lecture.video_url = video_rel_path

    # Clear existing chapters/lines for re-ingestion
    db.query(Chapter).filter(Chapter.lecture_id == lecture_id).delete()
    db.query(TranscriptLine).filter(TranscriptLine.lecture_id == lecture_id).delete()

    # Add Chapters (Table of Contents)
    toc_items = toc_data.get("table_of_contents", [])
    for i, item in enumerate(toc_items):
        start_sec = time_to_seconds(item.get("timestamp", "00:00:00"))

        # Calculate end_time: next item's timestamp or some large number
        if i < len(toc_items) - 1:
            end_sec = time_to_seconds(toc_items[i + 1].get("timestamp"))
        else:
            end_sec = start_sec + 3600.0  # Default 1 hour if last

        chapter = Chapter(
            lecture_id=lecture_id,
            title=item.get("topic_title", "Untitled"),
            summary=item.get("detailed_summary", ""),
            start_time=float(start_sec),
            end_time=float(end_sec),
        )
        db.add(chapter)

    # Add Transcript Lines
    for t_path in transcript_paths:
        lines = parse_transcript_text(t_path)
        for tl in lines:
            line = TranscriptLine(
                lecture_id=lecture_id,
                start_time=tl["start_time"],
                end_time=tl["end_time"],
                content=tl["content"],
            )
            db.add(line)

    db.commit()
    lecture_title = lecture.title
    db.close()
    print(f"Successfully ingested lecture: {lecture_id} ({lecture_title})")


if __name__ == "__main__":
    # This main block is now just for testing a single lecture
    # Real ingestion should be done via scripts/ingest_cs231n.py
    ingest_lecture(
        "lecture-1",
        "data/cs231n/ToC_Summary/lecture-1.json",
        [
            "data/cs231n/transcripts/Stanford_CS231N_Deep_Learning_for_Computer_Vision__Spring_2025__Lecture_1_Introduction_transcript.txt"
        ],
        video_rel_path="cs231n/videos/Stanford CS231N Deep Learning for Computer Vision ｜ Spring 2025 ｜ Lecture 1： Introduction.mp4",
    )
