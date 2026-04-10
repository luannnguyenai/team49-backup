import re

with open("src/services/llm_service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_gemini_func = False
gemini_func_lines = []

for line in lines:
    if line.startswith("from google import genai"):
        new_lines.append("# " + line)
    elif line.startswith("from google.genai import types"):
        new_lines.append("# " + line)
    elif line.startswith("from src.config import GEMINI_API_KEY, DEFAULT_MODEL"):
        new_lines.append("# from src.config import GEMINI_API_KEY\n")
        new_lines.append("from src.config import OPENAI_API_KEY, DEFAULT_MODEL\n")
        new_lines.append("from openai import OpenAI\n")
        new_lines.append("from src.services.sandbox import run_python_code\n")
    elif line.startswith("def get_context_and_stream_gemini"):
        in_gemini_func = True
        gemini_func_lines.append("# " + line)
    elif in_gemini_func:
        gemini_func_lines.append("# " + line)
    else:
        new_lines.append(line)

# Add the commented out function
new_lines.extend(gemini_func_lines)

# Write out the new function
openai_func = """
def get_context_and_stream_openai(lecture_id, current_timestamp, user_question, image_base64=None):
    db = SessionLocal()
    
    # 1. Get ToC
    chapters = db.query(Chapter).filter(Chapter.lecture_id == lecture_id).all()
    toc_context = "TABLE OF CONTENTS:\\n"
    for chap in chapters:
        start_ts = format_timestamp(chap.start_time)
        end_ts = format_timestamp(chap.end_time)
        toc_context += f"- [{start_ts} - {end_ts}] {chap.title}: {chap.summary}\\n"
        
    # 2. Get Transcript Window (+/- 5 mins = 600s total)
    start_window = max(0, current_timestamp - 300)
    end_window = current_timestamp + 300
    
    lines = db.query(TranscriptLine).filter(
        TranscriptLine.lecture_id == lecture_id,
        TranscriptLine.start_time >= start_window,
        TranscriptLine.start_time <= end_window
    ).order_by(TranscriptLine.start_time).all()
    
    transcript_context = "TRANSCRIPT WINDOW:\\n"
    for line in lines:
        ts = format_timestamp(line.start_time)
        transcript_context += f"[{ts}] {line.content}\\n"
        
    # 3. System Prompt
    system_instruction = '''Bạn là một Gia sư trực tuyến (AI Tutor) thông minh.
Nhiệm vụ: Giải đáp thắc mắc dựa trên bài giảng (Transcript + Hình ảnh).

QUY TẮC PHẢN HỒI:
1. Khi nhắc đến các đoạn trong bài giảng, LUÔN LUÔN sử dụng định dạng thời gian HH:MM:SS (ví dụ: 00:55:36) thay vì giây thô (ví dụ: 3336s).
2. Quan sát hình ảnh đính kèm (nếu có).
3. Câu hỏi trong Window/Hình ảnh: Trả lời chi tiết. Nếu LẠC ĐỀ: Nhắc tập trung.
4. ĐỐI VỚI CÁC CÂU HỎI TOÁN HỌC (từ mức trung bình trở lên): BẠN BUỘC PHẢI DÙNG CÔNG CỤ `run_python_code` ĐỂ TÍNH TOÁN VÀ ĐƯA RA KẾT QUẢ CHÍNH XÁC.
   - Môi trường Sandbox đã import sẵn: numpy, sympy, scipy, pandas.
   - Gợi ý: dùng `sympy.solve` hoặc `scipy.optimize` cho kết quả tối ưu nha.
'''

    curr_ts_str = format_timestamp(current_timestamp)
    user_prompt = f"Bài học:\\n{toc_context}\\n\\nThời điểm hiện tại ({curr_ts_str}):\\n{transcript_context}\\n\\nCâu hỏi: \\"{user_question}\\""

    content_list = [{"type": "text", "text": user_prompt}]
    if image_base64:
        content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })
        
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": content_list}
    ]
    
    tools = [{
        "type": "function",
        "function": {
            "name": "run_python_code",
            "description": "Thực thi script Python. Dùng để tính toán trực tiếp kết quả của bài toán. Luôn dùng hàm print() để in ra đáp án.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Mã đoạn code Python để in ra đáp án."
                    }
                },
                "required": ["code"]
            }
        }
    }]
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    full_answer = ""
    sandbox_output = ""
    
    try:
        # Phase 1: Call without stream to check for tool usage
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=tools,
            temperature=0.2
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            yield json.dumps({"a": "\\n*[Đang sử dụng Code Sandbox để tính toán...]*\\n"}) + "\\n"
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "run_python_code":
                    args = json.loads(tool_call.function.arguments)
                    code_to_run = args.get("code", "")
                    
                    sandbox_result = run_python_code(code_to_run)
                    sandbox_output += sandbox_result
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": sandbox_result,
                    })
            
            # Phase 2: Call again with tool results and stream=True
            stream = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                stream=True,
                temperature=0.2
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    text = chunk.choices[0].delta.content
                    full_answer += text
                    yield json.dumps({"a": text}) + "\\n"
                    
        else:
            if response_message.content:
                full_answer = response_message.content
                yield json.dumps({"a": full_answer}) + "\\n"

        history = QAHistory(
            lecture_id=lecture_id,
            question=user_question,
            answer=full_answer,
            thoughts=sandbox_output[:1000] if sandbox_output else "",
            current_timestamp=current_timestamp,
            image_base64=image_base64[:500] if image_base64 else None
        )
        db.add(history)
        db.commit()

        qa_logger.info(json.dumps({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lecture": lecture_id,
            "at": f"{current_timestamp:.1f}s",
            "q": user_question,
            "a": full_answer,
            "tools": sandbox_output != ""
        }, ensure_ascii=False))

    except Exception as e:
        qa_logger.error(f"Error: {e}")
        yield json.dumps({"e": str(e)}) + "\\n"
    finally:
        db.close()
"""
new_lines.append(openai_func)

with open("src/services/llm_service.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
