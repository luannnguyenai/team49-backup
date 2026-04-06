import os
import base64
import json
import logging
from datetime import datetime
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, DEFAULT_MODEL
from src.models.store import SessionLocal, Lecture, Chapter, TranscriptLine, QAHistory

# Configure File Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
qa_logger = logging.getLogger("QA_Tutor")
qa_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "qa_history.log"), encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
qa_logger.addHandler(file_handler)

def get_context_and_stream_gemini(lecture_id, current_timestamp, user_question, image_base64=None):
    db = SessionLocal()
    
    # 1. Get ToC
    chapters = db.query(Chapter).filter(Chapter.lecture_id == lecture_id).all()
    toc_context = "TABLE OF CONTENTS:\n"
    for chap in chapters:
        toc_context += f"- [{chap.start_time:.0f}s - {chap.end_time:.0f}s] {chap.title}: {chap.summary}\n"
        
    # 2. Get Transcript Window (+/- 5 mins = 600s total)
    start_window = max(0, current_timestamp - 300)
    end_window = current_timestamp + 300
    
    lines = db.query(TranscriptLine).filter(
        TranscriptLine.lecture_id == lecture_id,
        TranscriptLine.start_time >= start_window,
        TranscriptLine.start_time <= end_window
    ).order_by(TranscriptLine.start_time).all()
    
    transcript_context = "TRANSCRIPT WINDOW:\n"
    for line in lines:
        transcript_context += f"[{line.start_time:.0f}s] {line.content}\n"
        
    # 3. System Prompt
    system_instruction = """Bạn là một Gia sư trực tuyến (AI Tutor) thông minh.
Nhiệm vụ: Giải đáp thắc mắc dựa trên bài giảng (Transcript + Hình ảnh).

QUY TẮC:
1. Quan sát hình ảnh đính kèm (nếu có).
2. Câu hỏi trong Window/Hình ảnh: Trả lời chi tiết.
3. Nội dung ĐÃ HỌC: Tóm tắt lại.
4. Nội dung CHƯA HỌC: Nhắc user đợi.
5. LẠC ĐỀ: Nhắc tập trung bài giảng.
"""

    user_prompt = f"Bài học:\n{toc_context}\n\nHiện tại (giây {current_timestamp}):\n{transcript_context}\n\nCâu hỏi: \"{user_question}\""

    # 4. Prepare Content
    content_list = [user_prompt]
    if image_base64:
        try:
            image_data = base64.b64decode(image_base64)
            content_list.append(types.Part.from_bytes(data=image_data, mime_type="image/jpeg"))
        except Exception:
            pass  # Skip image if decode fails

    # 5. Stream from Gemini
    client = genai.Client(api_key=GEMINI_API_KEY)
    full_answer = ""
    
    try:
        stream = client.models.generate_content_stream(
            model=DEFAULT_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                thinking_config=types.ThinkingConfig(include_thoughts=True)
            ),
            contents=content_list
        )
        
        for chunk in stream:
            text = chunk.text or ""
            if text:
                full_answer += text
                yield json.dumps({"a": text}) + "\n"

        # 6. Save to DB
        history = QAHistory(
            lecture_id=lecture_id,
            question=user_question,
            answer=full_answer,
            thoughts="",
            current_timestamp=current_timestamp,
            image_base64=image_base64[:500] if image_base64 else None
        )
        db.add(history)
        db.commit()

        # 7. File Log
        qa_logger.info(json.dumps({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lecture": lecture_id,
            "at": f"{current_timestamp:.1f}s",
            "q": user_question,
            "a": full_answer
        }, ensure_ascii=False))

    except Exception as e:
        qa_logger.error(f"Error: {e}")
        yield json.dumps({"e": str(e)}) + "\n"
    finally:
        db.close()
