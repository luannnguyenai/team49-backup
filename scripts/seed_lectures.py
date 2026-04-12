"""
scripts/seed_lectures.py
------------------------
Seeds lecture data (Lecture, Chapter, TranscriptLine) from data/CS231n/ into
the PostgreSQL database using the sync engine from store.py.

Usage:
    python -m scripts.seed_lectures          # from project root
    docker compose exec backend python -m scripts.seed_lectures
"""

import glob
import json
import os
import re

from src.models.store import Chapter, Lecture, SessionLocal, TranscriptLine, init_db

DATA_DIR = "data/CS231n"
TOC_DIR = os.path.join(DATA_DIR, "ToC_Summary")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "transcripts")
VIDEO_DIR = os.path.join(DATA_DIR, "videos")


def ts_to_seconds(ts: str) -> float:
    """Convert HH:MM:SS or MM:SS to seconds."""
    parts = ts.strip().split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def parse_transcript(filepath: str) -> list[dict]:
    """Parse transcript file into list of {start_time, content}."""
    lines = []
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    # Skip header (everything before first timestamp)
    # Timestamps look like HH:MM:SS or MM:SS at start of line
    ts_pattern = re.compile(r"^(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})$", re.MULTILINE)
    matches = list(ts_pattern.finditer(raw))

    for i, match in enumerate(matches):
        ts = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        if content:
            lines.append(
                {
                    "start_time": ts_to_seconds(ts),
                    "content": content,
                }
            )

    return lines


def find_video_for_lecture(lecture_num: int) -> str | None:
    """Find video file matching lecture number."""
    pattern = os.path.join(VIDEO_DIR, f"*Lecture*{lecture_num}*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]  # return relative path
    return None


def find_transcript_for_lecture(lecture_num: int) -> str | None:
    """Find transcript file matching lecture number."""
    pattern = os.path.join(TRANSCRIPT_DIR, f"*Lecture_{lecture_num}*")
    matches = glob.glob(pattern)
    if not matches:
        pattern = os.path.join(TRANSCRIPT_DIR, f"*Lecture{lecture_num}*")
        matches = glob.glob(pattern)
    return matches[0] if matches else None


def seed():
    # Ensure tables exist
    init_db()

    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Lecture).count()
        if existing > 0:
            print(f"Database already has {existing} lectures. Skipping seed.")
            print("To re-seed, delete existing lectures first.")
            return

        toc_files = sorted(glob.glob(os.path.join(TOC_DIR, "lecture-*.json")))
        print(f"Found {len(toc_files)} ToC files")

        for toc_file in toc_files:
            # Extract lecture number from filename
            basename = os.path.basename(toc_file)
            num_match = re.search(r"lecture-(\d+)", basename)
            if not num_match:
                continue
            lecture_num = int(num_match.group(1))

            with open(toc_file, encoding="utf-8") as f:
                toc_data = json.load(f)

            lecture_id = f"cs231n-lecture-{lecture_num}"
            title = toc_data.get("lecture_title", f"Lecture {lecture_num}")
            video_path = find_video_for_lecture(lecture_num)

            # Create Lecture
            lecture = Lecture(
                id=lecture_id,
                title=title,
                description=f"CS231N Spring 2025 - Lecture {lecture_num}",
                video_url=video_path,
                duration=None,
            )
            db.add(lecture)
            db.flush()
            print(f"  + Lecture: {lecture_id} - {title[:60]}...")

            # Create Chapters from ToC
            sections = toc_data.get("table_of_contents", [])
            for i, section in enumerate(sections):
                start_ts = section.get("timestamp", "00:00:00")
                start_sec = ts_to_seconds(start_ts)
                # End time = next section start, or +600s for last
                if i + 1 < len(sections):
                    end_sec = ts_to_seconds(sections[i + 1].get("timestamp", "00:00:00"))
                else:
                    end_sec = start_sec + 600

                chapter = Chapter(
                    lecture_id=lecture_id,
                    title=section.get("topic_title", f"Section {i + 1}"),
                    summary=section.get("detailed_summary", "")[:500],
                    start_time=start_sec,
                    end_time=end_sec,
                )
                db.add(chapter)

            # Create TranscriptLines
            transcript_file = find_transcript_for_lecture(lecture_num)
            if transcript_file:
                lines = parse_transcript(transcript_file)
                for j, line in enumerate(lines):
                    end_time = (
                        lines[j + 1]["start_time"] if j + 1 < len(lines) else line["start_time"] + 5
                    )
                    tl = TranscriptLine(
                        lecture_id=lecture_id,
                        start_time=line["start_time"],
                        end_time=end_time,
                        content=line["content"],
                    )
                    db.add(tl)
                print(f"    + {len(lines)} transcript lines")
            else:
                print("    (no transcript found)")

        db.commit()
        total = db.query(Lecture).count()
        print(f"\nSeed complete! {total} lectures in database.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
