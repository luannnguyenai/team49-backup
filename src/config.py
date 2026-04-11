import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4-mini")
FAST_MODEL = os.getenv("FAST_MODEL", "gpt-5.4-nano")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
