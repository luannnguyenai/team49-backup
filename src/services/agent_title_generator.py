"""Generate concise conversation titles from the first user/assistant exchange.

Mirrors the ChatGPT pattern: after the first reply, summarize the chat into
3–6 words so the sidebar shows what the conversation is actually about.
"""

from __future__ import annotations

import logging
import re

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.services.chat_model_factory import build_chat_model_kwargs

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You name chat conversations. Read the user's first message and the "
    "assistant's reply, then return a single concise title that captures the "
    "topic. Rules: 3 to 6 words, Title Case, no quotes, no trailing "
    "punctuation, no emojis, no prefixes like 'Chat:' or 'Topic:'. "
    "Match the language of the user's message."
)

_MAX_TITLE_LEN = 60


def _sanitize(raw: str) -> str:
    text = raw.strip()
    text = text.strip("\"'`")
    text = re.split(r"[\r\n]", text, maxsplit=1)[0].strip()
    text = re.sub(r"^(title|topic|chat)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    text = text.rstrip(".!?,;:")
    if len(text) > _MAX_TITLE_LEN:
        text = text[:_MAX_TITLE_LEN].rstrip()
    return text


async def generate_conversation_title(
    user_message: str,
    assistant_message: str,
) -> str | None:
    """Return a short title or None if generation fails."""
    user_excerpt = (user_message or "").strip()[:600]
    assistant_excerpt = (assistant_message or "").strip()[:600]
    if not user_excerpt:
        return None

    try:
        llm = init_chat_model(
            **build_chat_model_kwargs(
                model=settings.default_model,
                temperature=0.2,
                max_tokens=40,
            )
        )
        prompt = (
            f"User message:\n{user_excerpt}\n\n"
            f"Assistant reply:\n{assistant_excerpt}\n\n"
            "Title:"
        )
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        content = getattr(response, "content", None)
        if isinstance(content, list):
            content = "".join(part if isinstance(part, str) else str(part) for part in content)
        if not isinstance(content, str):
            return None
        title = _sanitize(content)
        return title or None
    except Exception as exc:
        log.warning("Conversation title generation failed: %s", exc)
        return None
