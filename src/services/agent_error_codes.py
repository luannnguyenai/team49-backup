from __future__ import annotations


def classify_agent_error(exc: BaseException, default: str = "AGENT_CHAT_ERROR") -> str:
    """Map provider/runtime exceptions to stable user-facing support codes."""

    name = type(exc).__name__.lower()
    text = str(exc).lower()
    combined = f"{name} {text}"

    if "rate" in combined and ("limit" in combined or "429" in combined):
        return "AGENT_LLM_RATE_LIMIT"
    if "timeout" in combined or "timed out" in combined:
        return "AGENT_LLM_TIMEOUT"
    if "api_key" in combined or "authentication" in combined or "unauthorized" in combined:
        return "AGENT_LLM_AUTH_ERROR"
    if any(
        token in combined
        for token in (
            "provider",
            "llm",
            "model",
            "upstream",
            "inference",
            "completion",
            "generation",
        )
    ):
        return "AGENT_LLM_UNAVAILABLE"
    return default


def classify_rag_error(exc: BaseException, default: str = "RAG_RETRIEVAL_ERROR") -> str:
    """Map retrieval/search exceptions to stable user-facing support codes."""

    name = type(exc).__name__.lower()
    text = str(exc).lower()
    combined = f"{name} {text}"

    if "rate" in combined and ("limit" in combined or "429" in combined):
        return "RAG_PROVIDER_RATE_LIMIT"
    if "timeout" in combined or "timed out" in combined:
        return "RAG_TIMEOUT"
    if "index" in combined and any(
        token in combined for token in ("missing", "not found", "invalid")
    ):
        return "RAG_INDEX_INVALID"
    if "database" in combined or "asyncpg" in combined or "sqlalchemy" in combined:
        return "RAG_DATABASE_ERROR"
    if "parse" in combined or "json" in combined:
        return "RAG_RETRIEVAL_PARSE_ERROR"
    return default


def agent_system_error_message(error_code: str) -> str:
    return (
        "The AI assistant is temporarily unavailable due to a system incident. "
        f"Please try again later. Error code: {error_code}."
    )
