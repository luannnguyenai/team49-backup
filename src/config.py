"""
config.py
---------
Unified application settings loaded from environment variables via Pydantic Settings.
Merges original A20-App-049 config (LLM keys) with AI Personalized config (DB, Auth).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- LLM API Keys (original A20-App-049) ----
    anthropic_api_key: str = Field(default="", description="Anthropic Claude API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    default_model: str = Field(default="gemini-3-flash-preview", description="Default LLM model")
    fast_model: str = Field(default="gemini-2.5-flash", description="Fast model for minor tasks")
    model_provider: str = Field(default="gemini", description="LLM provider")
    log_level: str = Field(default="INFO", description="Logging level")

    # ---- Database (PostgreSQL async) ----
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_learning",
        description="Full asyncpg-compatible connection URL",
    )
    db_echo: bool = Field(default=False, description="Log all SQL statements")
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)

    # ---- Security / JWT ----
    secret_key: str = Field(default="change_me_in_production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    rate_limit_login_per_minute: int = Field(default=5)

    # ---- App ----
    app_name: str = "AI Adaptive Learning Platform"
    debug: bool = False


settings = Settings()

# ---- Backward-compatible aliases for existing code ----
ANTHROPIC_API_KEY = settings.anthropic_api_key
OPENAI_API_KEY = settings.openai_api_key
GEMINI_API_KEY = settings.gemini_api_key
DEFAULT_MODEL = settings.default_model
FAST_MODEL = settings.fast_model
MODEL_PROVIDER = settings.model_provider
LOG_LEVEL = settings.log_level
