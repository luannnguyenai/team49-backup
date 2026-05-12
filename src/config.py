"""
config.py
---------
Unified application settings loaded from environment variables via Pydantic Settings.
Merges original A20-App-049 config (LLM keys) with AI Personalized config (DB, Auth).
"""

import json
from collections.abc import Mapping
from typing import Annotated, Any, Literal

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
    model_provider: str = Field(default="openai", description="LLM provider")
    model_reasoning_effort: Literal["off", "low", "medium", "high", "xhigh"] = Field(
        default="medium",
        description="Optional reasoning effort for providers that support it.",
    )
    model_extra_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific chat model kwargs, parsed from JSON.",
    )
    qwen35_4b_model: str = Field(
        default="qwen3.5-4b-lora",
        description="OpenAI-compatible local Qwen chat model id.",
    )
    qwen35_4b_base_url: str = Field(
        default="https://vllm.a20-app-049.io.vn/v1",
        description="OpenAI-compatible local Qwen API base URL.",
    )
    qwen35_4b_api_key: str = Field(
        default="EMPTY",
        description="API key placeholder for local OpenAI-compatible Qwen servers.",
    )
    llm_request_timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Per-provider LLM request timeout in seconds.",
    )
    llm_max_retries: int = Field(
        default=1,
        ge=0,
        description="Maximum provider retry attempts for LLM requests.",
    )
    guardrail_router_base_url: str = Field(
        default="",
        description="OpenAI-compatible /v1 base URL for the Cloudflare Tunnel vLLM guardrail router.",
    )
    guardrail_router_model: str = Field(
        default="guardrail-router-merged",
        description="Model name served by the guardrail router.",
    )
    guardrail_router_api_key: str = Field(
        default="",
        description="Bearer token for the OpenAI-compatible guardrail router endpoint.",
    )
    guardrail_router_cf_access_client_id: str = Field(
        default="",
        description="Cloudflare Access service token client ID for the guardrail router tunnel.",
    )
    guardrail_router_cf_access_client_secret: str = Field(
        default="",
        description="Cloudflare Access service token client secret for the guardrail router tunnel.",
    )
    guardrail_router_timeout_seconds: float = Field(
        default=10.0,
        ge=0.1,
        description="Timeout for each guardrail router endpoint attempt.",
    )
    guardrail_router_unhealthy_cooldown_seconds: float = Field(
        default=60.0,
        ge=0.0,
        description="Seconds to skip the local guardrail router after a failed endpoint attempt.",
    )
    guardrail_router_fallback_provider: str = Field(
        default="",
        description="Fallback provider for guardrail routing after the Cloudflare Tunnel vLLM route fails.",
    )
    guardrail_router_fallback_model: str = Field(
        default="",
        description="Fallback model for guardrail routing after the Cloudflare Tunnel vLLM route fails.",
    )
    guardrail_router_max_tokens: int = Field(
        default=96,
        ge=1,
        description="Maximum output tokens for guardrail router JSON decisions.",
    )
    external_research_enabled: bool = Field(
        default=False,
        description="Enable the experimental external web/paper search mode.",
    )
    semantic_scholar_api_key: str = Field(
        default="",
        description="Optional Semantic Scholar API key for external paper search.",
    )
    chat_model_health_timeout_seconds: float = Field(
        default=8.0,
        ge=1.0,
        description="Timeout for lightweight chat model health checks.",
    )
    gemini_requests_per_minute: int = Field(
        default=15,
        ge=1,
        description="Client-side throttle for Gemini API requests per minute.",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key")
    langfuse_base_url: str = Field(
        default="https://cloud.langfuse.com",
        description="Preferred Langfuse base URL",
    )
    langfuse_host: str = Field(
        default="",
        description="Backward-compatible Langfuse host alias",
    )

    # ---- Database (PostgreSQL async) ----
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:change_me_strong_password@localhost:5433/ai_learning",
        description="Full asyncpg-compatible connection URL",
    )
    agent_graph_checkpointer_backend: Literal["memory", "postgres"] = Field(
        default="postgres",
        description="LangGraph checkpointer backend for /agent graph state.",
    )
    agent_graph_checkpointer_setup: bool = Field(
        default=True,
        description="Run LangGraph checkpointer setup before graph use. Disable after schema is managed separately.",
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
    rate_limit_forgot_password_per_hour: int = Field(default=5)
    asset_url_expire_seconds: int = Field(default=900)

    # ---- Asset delivery (local vs AWS S3 + CloudFront) ----
    # Default `local` keeps the existing /data/{asset_path} flow intact for dev.
    # Set to `s3` on Render production to return CloudFront URLs instead.
    asset_storage_provider: Literal["local", "s3"] = Field(
        default="local",
        description="Asset delivery mode: 'local' for /data/* signed URLs, 's3' for CloudFront URLs.",
    )
    aws_region: str = Field(default="", description="AWS region for the S3 asset bucket.")
    aws_s3_bucket: str = Field(
        default="", description="Private S3 bucket name holding course assets."
    )
    aws_s3_prefix: str = Field(
        default="courses",
        description="Key prefix inside the S3 bucket where course assets live.",
    )
    cloudfront_domain: str = Field(
        default="",
        description="CloudFront domain name (no scheme), e.g. 'd123.cloudfront.net' or 'cdn.example.com'.",
    )
    cloudfront_key_pair_id: str = Field(
        default="",
        description="CloudFront public key ID; required only when issuing signed URLs.",
    )
    cloudfront_private_key: str = Field(
        default="",
        description="CloudFront private key PEM contents; required only when issuing signed URLs.",
    )

    gmail_app_password: str = Field(default="")
    email_from: str = Field(default="")
    frontend_base_url: str = Field(default="http://localhost:3000")
    password_reset_token_ttl_minutes: int = Field(default=30, ge=1)

    # ---- Redis ----
    redis_url: str = Field(
        default="redis://:redis123secure@localhost:6379/0",
        description="Redis URL for rate limiting + token denylist",
    )

    # ---- CORS ----
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ],
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

    # ---- Placement Assessment Strategies ----
    cold_start_mode: Literal["random_uniform", "spread_by_prior", "irt_adaptive", "auto"] = Field(
        default="spread_by_prior",
        description="Item selection strategy for placement assessments: random_uniform | spread_by_prior | irt_adaptive | auto",
    )
    irt_min_avg_responses: int = Field(
        default=200,
        ge=1,
        description="Minimum average responses per item to qualify for IRT adaptive selection",
    )
    irt_min_calibrated_ratio: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum fraction of items with is_calibrated=true for IRT adaptive",
    )
    irt_max_median_se_b: float = Field(
        default=0.3,
        ge=0.0,
        description="Maximum median standard error of difficulty parameter for IRT adaptive",
    )
    irt_exposure_cap_hours: int = Field(
        default=24,
        ge=0,
        description="Hours to look back for item exposure cap in IRT adaptive selection",
    )
    irt_use_2pl: bool = Field(
        default=False,
        description="Use 2PL (guessing=0) instead of 3PL-lite (guessing=0.25) for IRT Fisher info",
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

    @field_validator("model_extra_kwargs", mode="before")
    @classmethod
    def parse_any_mapping(cls, value: Any) -> dict[str, Any]:
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, Mapping):
            raise ValueError("value must be a mapping or JSON object string")
        return dict(value)


settings = Settings()

# ---- Backward-compatible aliases for existing code ----
ANTHROPIC_API_KEY = settings.anthropic_api_key
OPENAI_API_KEY = settings.openai_api_key
GEMINI_API_KEY = settings.gemini_api_key
DEFAULT_MODEL = settings.default_model
FAST_MODEL = settings.fast_model
MODEL_PROVIDER = settings.model_provider
LOG_LEVEL = settings.log_level
