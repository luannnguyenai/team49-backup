# Workflow: Ingestion & Deployment for CS231N

This workflow describes how to add new lecture data and deploy the platform using Docker.

## 1. Data Preparation

1.  **Dữ liệu Video & Transcript**: Tải toàn bộ thư mục `data/` từ Google Drive của nhóm và giải nén vào thư mục gốc dự án.
2.  **ToC Summary (Cho bài giảng mới)**:
    - Use the prompt in `prompts/lecture_extraction_prompt.txt` with the transcript in a tool like Claude/Gemini.
    - Save the resulting JSON in `data/cs231n/ToC_Summary/lecture-X.json`.
    - Format should match:
      ```json
      {
        "lecture_id": "cs231n_lecture_X",
        "chapters": [
          { "title": "Topic Name", "start_time": "HH:MM:SS", "summary": "..." },
          ...
        ]
      }
      ```

## 2. Database Ingestion

// turbo
Run the ingestion script to synchronize local files with the database:
```bash
PYTHONPATH=. uv run python scripts/ingest_cs231n.py
```
*Note: This script automatically sanitizes titles to follow the "Lecture X: Topic" format.*

## 3. Docker Deployment

If first time, ensure your `.env` file has the `GEMINI_API_KEY`.

// turbo
Start the services:
```bash
docker compose up -d
```

Check logs to verify everything is running:
```bash
docker compose logs -f
```

## 4. Verification

1. Access the UI:
   - Browse to `http://localhost:8000` for the main interface.
   - Browse to `http://localhost:8501` for the Streamlit lab interface.
2. Select the new lecture from the dropdown and verify the video and ToC load correctly.
