"""
scripts/migrate_sqlite.py
-------------------------
Migrates existing lecture data from SQLite (app.db) to PostgreSQL.
Usage: python scripts/migrate_sqlite.py
"""

import os
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models.store import Chapter, Lecture, QAHistory, TranscriptLine

# Sync sync engine for PG
_SYNC_DATABASE_URL = settings.database_url.replace("+asyncpg", "").replace(
    "postgresql://", "postgresql+psycopg2://"
)
pg_engine = create_engine(_SYNC_DATABASE_URL)
PGSession = sessionmaker(bind=pg_engine)


def migrate():
    sqlite_path = "app.db"
    if not os.path.exists(sqlite_path):
        print(f"SQLite database {sqlite_path} not found. Skipping migration.")
        return

    print(f"Connecting to SQLite: {sqlite_path}")
    sl_conn = sqlite3.connect(sqlite_path)
    sl_cursor = sl_conn.cursor()

    print("Connecting to PostgreSQL...")
    pg_db = PGSession()

    # 1. Lectures
    print("Migrating Lectures...")
    sl_cursor.execute(
        "SELECT id, title, description, video_url, duration, created_at FROM lectures"
    )
    for row in sl_cursor.fetchall():
        pg_db.add(
            Lecture(
                id=row[0],
                title=row[1],
                description=row[2],
                video_url=row[3],
                duration=row[4],
                created_at=row[5],
            )
        )

    # 2. Chapters
    print("Migrating Chapters...")
    sl_cursor.execute("SELECT lecture_id, title, summary, start_time, end_time FROM chapters")
    for row in sl_cursor.fetchall():
        pg_db.add(
            Chapter(
                lecture_id=row[0], title=row[1], summary=row[2], start_time=row[3], end_time=row[4]
            )
        )

    # 3. Transcript Lines
    print("Migrating Transcript Lines...")
    sl_cursor.execute("SELECT lecture_id, start_time, end_time, content FROM transcript_lines")
    for row in sl_cursor.fetchall():
        pg_db.add(
            TranscriptLine(lecture_id=row[0], start_time=row[1], end_time=row[2], content=row[3])
        )

    # 4. QA History
    print("Migrating QA History...")
    sl_cursor.execute(
        "SELECT lecture_id, question, answer, thoughts, current_timestamp, image_base64, created_at FROM qa_history"
    )
    for row in sl_cursor.fetchall():
        pg_db.add(
            QAHistory(
                lecture_id=row[0],
                question=row[1],
                answer=row[2],
                thoughts=row[3],
                current_timestamp=row[4],
                image_base64=row[5],
                created_at=row[6],
            )
        )

    print("Committing to PostgreSQL...")
    pg_db.commit()
    pg_db.close()
    sl_conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    migrate()
