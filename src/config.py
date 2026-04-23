"""
config.py
---------
Unified application settings loaded from environment variables via Pydantic Settings.
Merges original A20-App-049 config (LLM keys) with AI Personalized config (DB, Auth).
"""

import json
from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    default_model: str = Field(
        default="gpt-5.4-mini",
        description="Default LLM model",
    )
    fast_model: str = Field(
        default="gpt-5.4-nano",
        description="Fast model for minor tasks",
    )
    model_provider: str = Field(default ="openai", description="LLM provider")
    gemini_requests_per_minute: int = Field(
        default=15,
        ge=1,
        description="Client-side throttle for Gemini API requests per minute.",
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # ---- Database (PostgreSQL async) ----
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:change_me_strong_password@localhost:5432/ai_learning",
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
    asset_url_expire_seconds: int = Field(default=900)

    # ---- Redis ----
    redis_url: str = Field(
        default="redis://:redis123secure@localhost:6379/0",
        description="Redis URL for rate limiting + token denylist",
    )

    # ---- CORS ----
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins. Never use ['*'] with credentials=True.",
    )

    # ---- App ----
    app_name: str = "AI Adaptive Learning Platform"
    debug: bool = False
    kg_phase: int = Field(default=0, ge=0, le=1, description="Knowledge Graph build phase")
    admin_token: str = Field(default="", description="Admin token for protected ops endpoints")
    kg_mastery_skip_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    kg_mastery_review_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    kg_shortcut_mastery_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    kg_shortcut_hours_factor: float = Field(default=0.4, ge=0.0, le=1.0)
    kg_path_week_buffer: float = Field(default=0.2, ge=0.0)
    kg_bucket_weights: dict[str, float] = Field(
        default_factory=lambda: {"easy": 1.0, "medium": 1.3, "hard": 1.6}
    )
    kg_recsys_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "mastery_gap": 0.35,
            "prereq_ready": 0.25,
            "transfer_boost": 0.2,
            "goal_distance": 0.15,
            "freshness": 0.05,
        }
    )
    write_goal_preferences_enabled: bool = Field(
        default=True,
        description="Write runtime goal preference snapshots to goal_preferences.",
    )
    write_learner_mastery_kp_enabled: bool = Field(
        default=True,
        description="Write mastery updates to learner_mastery_kp.",
    )
    write_waived_units_enabled: bool = Field(
        default=True,
        description="Write skip/waive audit records to waived_units.",
    )
    write_planner_audit_enabled: bool = Field(
        default=True,
        description="Write planner audit rows into plan_history, rationale_log, and planner_session_state.",
    )
    read_goal_preferences_enabled: bool = Field(
        default=True,
        description="Read learner goals from goal_preferences.",
    )
    read_learner_mastery_kp_enabled: bool = Field(
        default=True,
        description="Read learner mastery from learner_mastery_kp.",
    )
    read_canonical_questions_enabled: bool = Field(
        default=True,
        description="Read assessment/quiz items from canonical question_bank.",
    )
    write_canonical_interactions_enabled: bool = Field(
        default=True,
        description="Write canonical question item IDs into interactions.",
    )
    read_canonical_planner_enabled: bool = Field(
        default=True,
        description="Read planner candidates from canonical learning units and prerequisite graph.",
    )
    allow_legacy_question_reads: bool = Field(
        default=False,
        description="Allow fallback reads from legacy questions/topics.",
    )
    allow_legacy_mastery_writes: bool = Field(
        default=False,
        description="Allow fallback writes into legacy mastery_scores.",
    )
    allow_legacy_mastery_reads: bool = Field(
        default=False,
        description="Allow fallback reads from legacy mastery_scores.",
    )
    allow_legacy_planner_writes: bool = Field(
        default=False,
        description="Allow fallback writes into legacy learning_paths.",
    )
    allow_legacy_topic_content_reads: bool = Field(
        default=False,
        description="Allow fallback content reads backed by legacy modules/topics.",
    )
    allow_legacy_kg_routes: bool = Field(
        default=False,
        description="Allow legacy KG routes backed by modules/topics/questions/knowledge_components.",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []

            if value.startswith("["):
                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON must decode to a list.")
                return [str(item).strip() for item in parsed if str(item).strip()]

            return [item.strip() for item in value.split(",") if item.strip()]

        raise ValueError("CORS_ORIGINS must be a list or a string.")

    @field_validator("kg_bucket_weights", "kg_recsys_weights", mode="before")
    @classmethod
    def parse_float_mapping(cls, value: Any) -> dict[str, float]:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, Mapping):
            raise ValueError("value must be a mapping or JSON object string")
        return {str(key): float(item) for key, item in value.items()}


settings = Settings()

# ---- Backward-compatible aliases for existing code ----
ANTHROPIC_API_KEY = settings.anthropic_api_key
OPENAI_API_KEY = settings.openai_api_key
GEMINI_API_KEY = settings.gemini_api_key
DEFAULT_MODEL = settings.default_model
FAST_MODEL = settings.fast_model
MODEL_PROVIDER = settings.model_provider
LOG_LEVEL = settings.log_level
