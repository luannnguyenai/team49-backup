"""Debug test - inspect chunk structure in detail."""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = os.getenv("DEFAULT_MODEL", "gemini-3-flash-preview")

print(f"Model: {model}")
print("=" * 60)

stream = client.models.generate_content_stream(
    model=model,
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(include_thoughts=True)
    ),
    contents="1+1=?"
)

for i, chunk in enumerate(stream):
    print(f"\n--- Chunk {i} ---")
    if chunk.candidates and chunk.candidates[0].content.parts:
        for j, part in enumerate(chunk.candidates[0].content.parts):
            # Print ALL attributes of the part
            print(f"  Part {j}:")
            print(f"    type: {type(part)}")
            print(f"    text: '{part.text[:100] if hasattr(part, 'text') and part.text else 'N/A'}'")
            print(f"    thought: {getattr(part, 'thought', 'ATTR_NOT_EXIST')}")
            # List all non-private attributes
            attrs = [a for a in dir(part) if not a.startswith('_')]
            print(f"    all attrs: {attrs}")
    if i > 5:
        print("\n... (stopping after 6 chunks)")
        break
