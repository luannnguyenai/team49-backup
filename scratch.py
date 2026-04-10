import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Calculate the sum of the first 20 primes",
    config=types.GenerateContentConfig(
        tools=[{"code_execution": {}}]
    )
)
print(response.text)
