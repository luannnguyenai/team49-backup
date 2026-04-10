import re

with open("src/api/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Comment out gemini import
content = content.replace(
    "from src.services.llm_service import get_context_and_stream_gemini",
    "# from src.services.llm_service import get_context_and_stream_gemini\nfrom src.services.llm_service import get_context_and_stream_openai"
)

# Comment out gemini generator call and add openai generator call
old_call = """        generator = get_context_and_stream_gemini(
            req.lecture_id, 
            req.current_timestamp, 
            req.question,
            image_base64=req.image_base64
        )"""

new_call = """        # generator = get_context_and_stream_gemini(
        #     req.lecture_id, 
        #     req.current_timestamp, 
        #     req.question,
        #     image_base64=req.image_base64
        # )
        generator = get_context_and_stream_openai(
            req.lecture_id, 
            req.current_timestamp, 
            req.question,
            image_base64=req.image_base64
        )"""

content = content.replace(old_call, new_call)

with open("src/api/app.py", "w", encoding="utf-8") as f:
    f.write(content)
