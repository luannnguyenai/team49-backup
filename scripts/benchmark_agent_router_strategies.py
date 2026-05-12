from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from src.config import settings
from src.schemas.agent import AgentIntent
from src.services.agent_graph_contracts import AgentRoute
from src.services.agent_router_factory import build_production_agent_router
from src.services.agent_structured_router import StructuredAgentRouter
from src.services.chat_model_factory import build_chat_model_kwargs
from src.services.model_registry import DEFAULT_CHAT_MODEL_ID
from src.services.openai_compatible_http_chat_model import OpenAICompatibleHTTPChatModel

StrategyName = Literal[
    "baseline_fast_model",
    "baseline_0_8b",
    "fast_model",
    "deterministic",
    "deterministic_compact",
    "content_fastpath_compact",
    "compact_all",
    "compact_labeled_all",
    "compact_decision_table_all",
    "compact_fewshot_all",
    "retrieval_first",
    "retrieval_first_compact",
    "retrieval_first_labeled_compact",
]


def default_strategy_names() -> list[StrategyName]:
    return [
        "baseline_fast_model",
        "baseline_0_8b",
        "compact_all",
        "compact_labeled_all",
        "compact_decision_table_all",
        "compact_fewshot_all",
    ]


def needs_compact_model(strategies: list[StrategyName]) -> bool:
    return any(
        item
        in (
            "deterministic_compact",
            "content_fastpath_compact",
            "compact_all",
            "compact_labeled_all",
            "compact_decision_table_all",
            "compact_fewshot_all",
            "retrieval_first_compact",
            "retrieval_first_labeled_compact",
        )
        for item in strategies
    )


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    message: str
    expected_intent: AgentIntent
    expected_topic_contains: str | None = None
    active_topic: str | None = None
    recent_messages: list[dict[str, Any]] | None = None
    route_context: dict[str, Any] | None = None


class CompactRouteOutput(BaseModel):
    intent: AgentIntent
    topic: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    clarify: str | None = None


@dataclass
class StrategyResult:
    strategy: str
    case: str
    latency_ms: float
    intent: str
    topic: str | None
    confidence: float
    clarify: str | None
    intent_ok: bool
    topic_ok: bool | None
    score: float
    error: str | None = None


CONTENT_PREFIX_PATTERNS = [
    r"^\s*cho (?:tôi|mình) (?:thông tin|nội dung)(?: cụ thể hơn| thêm)? về\s+",
    r"^\s*cho (?:tôi|mình) hỏi về\s+",
    r"^\s*(?:giải thích|trình bày|tìm|tìm cho mình|tìm cho tôi)(?: thêm| kỹ hơn| cụ thể hơn)?\s+",
    r"^\s*(?:explain|find|search|tell me about|more detail about|give me more detail about)\s+",
]

CONTROL_PATTERNS: list[tuple[AgentIntent, tuple[str, ...]]] = [
    (
        "request_replan",
        (
            "replan",
            "recalculate",
            "optimize my path",
            "tối ưu lộ trình",
            "tối ưu lại lộ trình",
            "học lại lộ trình",
        ),
    ),
    (
        "request_path_switch",
        (
            "switch path",
            "change path",
            "đổi lộ trình",
            "chuyển lộ trình",
            "chuyển tôi sang lộ trình",
            "chuyển sang lộ trình",
        ),
    ),
    ("assess_knowledge", ("quiz me", "test me", "kiểm tra", "làm quiz", "đánh giá")),
    ("assistant_help", ("hello", "hi", "xin chào", "bạn làm được gì", "what can you do")),
]


def default_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            name="vi_content_mask_rcnn",
            message="cho tôi thông tin cụ thể hơn về Mask R-CNN",
            expected_intent="find_content",
            expected_topic_contains="Mask R-CNN",
        ),
        BenchmarkCase(
            name="en_content_attention",
            message="Explain attention mechanisms in transformers",
            expected_intent="find_content",
            expected_topic_contains="attention",
        ),
        BenchmarkCase(
            name="short_followup_active_topic",
            message="kiến trúc chi tiết hơn",
            active_topic="Mask R-CNN",
            recent_messages=[
                {"role": "assistant", "content": "We were discussing Mask R-CNN."},
            ],
            expected_intent="find_content",
            expected_topic_contains="Mask R-CNN",
        ),
        BenchmarkCase(
            name="assistant_help",
            message="xin chào",
            expected_intent="assistant_help",
        ),
        BenchmarkCase(
            name="request_replan",
            message="tôi đã biết CNN rồi, tối ưu lại lộ trình cho tôi",
            expected_intent="request_replan",
        ),
        BenchmarkCase(
            name="path_switch",
            message="chuyển tôi sang lộ trình NLP",
            expected_intent="request_path_switch",
        ),
        BenchmarkCase(
            name="assessment",
            message="quiz me on object detection",
            expected_intent="assess_knowledge",
            expected_topic_contains="object detection",
        ),
    ]


def load_cases(path: str | None) -> list[BenchmarkCase]:
    if not path:
        return default_cases()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [BenchmarkCase(**item) for item in payload]


def _clean_topic(value: str) -> str:
    topic = value.strip(" .?!:;\"'")
    topic = re.sub(r"\s+", " ", topic)
    return topic


def _extract_content_topic(message: str) -> str | None:
    text = message.strip()
    for pattern in CONTENT_PREFIX_PATTERNS:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_topic(text[match.end() :])
    acronym = re.search(r"\b[A-Z][A-Z0-9]*(?:[- ][A-Z0-9]+)+\b|\b[A-Z]{3,}[A-Za-z0-9-]*\b", text)
    if acronym:
        return _clean_topic(acronym.group(0))
    return None


def _extract_assessment_topic(message: str) -> str | None:
    patterns = [
        r"\bquiz me on\s+",
        r"\btest me on\s+",
        r"\bquiz me about\s+",
        r"\btest me about\s+",
        r"\bkiểm tra (?:tôi|mình)?(?: về)?\s+",
        r"\blàm quiz(?: về)?\s+",
    ]
    text = message.strip()
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_topic(text[match.end() :])
    return None


def deterministic_content_route(case: BenchmarkCase) -> CompactRouteOutput:
    message = case.message.strip()
    lowered = message.casefold()
    for intent, needles in CONTROL_PATTERNS:
        if any(re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", lowered) for needle in needles):
            topic = _extract_assessment_topic(message) if intent == "assess_knowledge" else None
            return CompactRouteOutput(intent=intent, topic=topic, confidence=0.85, clarify=None)

    if case.active_topic and len(message.split()) <= 8:
        return CompactRouteOutput(
            intent="find_content",
            topic=_clean_topic(f"{case.active_topic} {message}"),
            confidence=0.88,
            clarify=None,
        )

    topic = _extract_content_topic(message)
    if topic:
        return CompactRouteOutput(
            intent="find_content",
            topic=topic,
            confidence=0.86,
            clarify=None,
        )

    return CompactRouteOutput(
        intent="clarify",
        topic=None,
        confidence=0.45,
        clarify="What topic or course action should I help with?",
    )


def deterministic_content_fast_path(case: BenchmarkCase) -> CompactRouteOutput | None:
    message = case.message.strip()
    lowered = message.casefold()
    if any(
        re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", lowered)
        for _, needles in CONTROL_PATTERNS
        for needle in needles
    ):
        return None

    if case.active_topic and len(message.split()) <= 8:
        return CompactRouteOutput(
            intent="find_content",
            topic=_clean_topic(f"{case.active_topic} {message}"),
            confidence=0.88,
            clarify=None,
        )

    topic = _extract_content_topic(message)
    if topic:
        return CompactRouteOutput(
            intent="find_content",
            topic=topic,
            confidence=0.86,
            clarify=None,
        )
    return None


def route_quality(case: BenchmarkCase, output: CompactRouteOutput) -> dict[str, Any]:
    intent_ok = output.intent == case.expected_intent or (
        case.expected_intent == "find_content" and output.intent == "explain_concept"
    )
    topic_ok: bool | None = None
    if case.expected_topic_contains:
        topic_ok = case.expected_topic_contains.casefold() in (output.topic or "").casefold()
    score_parts = [intent_ok]
    if topic_ok is not None:
        score_parts.append(topic_ok)
    score = sum(1.0 for item in score_parts if item) / len(score_parts)
    return {"intent_ok": intent_ok, "topic_ok": topic_ok, "score": score}


def _from_agent_route(route: AgentRoute) -> CompactRouteOutput:
    return CompactRouteOutput(
        intent=route.intent,
        topic=route.extracted_slots.raw_topic,
        confidence=route.confidence,
        clarify=route.clarification_question,
    )


def _build_fast_model_router() -> StructuredAgentRouter:
    from langchain.chat_models import init_chat_model

    return StructuredAgentRouter(
        model=init_chat_model(
            **build_chat_model_kwargs(
                model=settings.fast_model,
                model_provider=settings.model_provider,
                temperature=0,
                reasoning_effort=getattr(settings, "model_reasoning_effort", None),
                extra_kwargs=getattr(settings, "model_extra_kwargs", None),
            )
        )
    )


def _build_compact_router_model() -> OpenAICompatibleHTTPChatModel:
    return OpenAICompatibleHTTPChatModel(
        model=settings.guardrail_router_model,
        base_url=settings.guardrail_router_base_url,
        api_key=settings.guardrail_router_api_key,
        temperature=0,
        timeout=settings.guardrail_router_timeout_seconds,
        max_retries=0,
    )


def build_compact_router_messages(
    case: BenchmarkCase,
    *,
    labeled: bool = False,
    variant: str | None = None,
) -> list[dict[str, str]]:
    prompt_variant = variant or ("labeled" if labeled else "plain")
    if prompt_variant == "fewshot":
        system = (
            "Classify one AI/ML learning assistant request. Return only compact JSON with keys "
            "intent, topic, confidence, clarify. No markdown. confidence is 0..1. "
            "Allowed intents: explain_concept, find_content, navigate_to_unit, ask_what_next, "
            "assess_knowledge, request_replan, explain_planner_decision, summarize_progress, "
            "general_course_question, assistant_help, request_path_switch, clarify. "
            "Choose the action intent before content if the user asks to change workflow. "
            "Examples:\n"
            "User: tối ưu lại lộ trình cho tôi\n"
            '{"intent":"request_replan","topic":null,"confidence":0.92,"clarify":null}\n'
            "User: chuyển tôi sang lộ trình NLP\n"
            '{"intent":"request_path_switch","topic":"NLP","confidence":0.92,"clarify":null}\n'
            "User: quiz me on object detection\n"
            '{"intent":"assess_knowledge","topic":"object detection","confidence":0.9,"clarify":null}\n'
            "User: cho tôi thông tin cụ thể hơn về Mask R-CNN\n"
            '{"intent":"find_content","topic":"Mask R-CNN","confidence":0.9,"clarify":null}'
        )
    elif prompt_variant == "decision_table":
        system = (
            "Classify one AI/ML learning assistant request. Return only JSON with keys "
            "intent, topic, confidence, clarify. confidence must be a decimal from 0 to 1. "
            "Allowed intents: explain_concept, find_content, navigate_to_unit, ask_what_next, "
            "assess_knowledge, request_replan, explain_planner_decision, summarize_progress, "
            "general_course_question, assistant_help, request_path_switch, clarify. "
            "Priority order: "
            "1 request_path_switch for switching path/track/course/domain. Do not classify path changes as navigate_to_unit. "
            "2 request_replan for rebuilding or optimizing the learning path. "
            "3 assess_knowledge for quiz/test/check knowledge. "
            "4 assistant_help for greeting/help. "
            "5 find_content or explain_concept for searching/explaining course content. "
            "6 clarify only when intent or topic is missing. "
            "Topic rules: path switch topic is the target path; assessment topic is tested topic; content topic is searchable concept. "
            "Use null for missing topic or clarify."
        )
    elif prompt_variant == "labeled":
        system = (
            "Classify one AI/ML learning assistant request. Return only JSON with exactly these keys: "
            "intent, topic, confidence, clarify. confidence must be a decimal from 0 to 1, not percent. "
            "Allowed intents: explain_concept, find_content, navigate_to_unit, ask_what_next, "
            "assess_knowledge, request_replan, explain_planner_decision, summarize_progress, "
            "general_course_question, assistant_help, request_path_switch, clarify. "
            "Definitions: request_replan means the user asks to rebuild or optimize the learning path; "
            "request_path_switch means the user asks to switch to another path, track, course, or domain; "
            "assess_knowledge means the user asks for a quiz, test, or knowledge check; "
            "assistant_help means greeting or asking what the assistant can do; "
            "find_content or explain_concept means the user asks for course content or an explanation. "
            "Examples: 'tối ưu lại lộ trình cho tôi' -> request_replan; "
            "'chuyển tôi sang lộ trình NLP' -> request_path_switch; "
            "'quiz me on object detection' -> assess_knowledge. "
            "Use topic only for searchable course content or assessment topic. Use English or Vietnamese clarify text only."
        )
    else:
        system = (
            "Classify one AI/ML learning assistant request. Return only JSON with exactly these keys: "
            "intent, topic, confidence, clarify. confidence must be a decimal from 0 to 1, not percent. "
            "intent must be one of: explain_concept, find_content, "
            "navigate_to_unit, ask_what_next, assess_knowledge, request_replan, "
            "explain_planner_decision, summarize_progress, general_course_question, "
            "assistant_help, request_path_switch, clarify. Use topic only for searchable course "
            "content. Use English or Vietnamese clarify text only."
        )
    user = (
        f"Active topic: {case.active_topic or ''}\n"
        f"Recent messages: {case.recent_messages or []}\n"
        f"Message: {case.message}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def compact_router_route(
    case: BenchmarkCase,
    model: OpenAICompatibleHTTPChatModel,
    *,
    labeled: bool = False,
    variant: str | None = None,
) -> CompactRouteOutput:
    response = model.invoke(build_compact_router_messages(case, labeled=labeled, variant=variant))
    content = str(response.content).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(content[start : end + 1])
    try:
        intent = str(parsed.get("intent") or "").strip()
        intent_aliases = {
            "hello": "assistant_help",
            "greeting": "assistant_help",
            "help": "assistant_help",
            "replan": "request_replan",
            "path_switch": "request_path_switch",
            "switch_path": "request_path_switch",
            "quiz": "assess_knowledge",
            "assessment": "assess_knowledge",
        }
        confidence = parsed.get("confidence", 0.0)
        if isinstance(confidence, (int, float)) and confidence > 1:
            confidence = confidence / 100
        return CompactRouteOutput.model_validate(
            {
                "intent": intent_aliases.get(intent, intent),
                "topic": parsed.get("topic") or None,
                "confidence": confidence,
                "clarify": parsed.get("clarify") or None,
            }
        )
    except ValidationError:
        raise


async def run_strategy_case(
    strategy: StrategyName,
    case: BenchmarkCase,
    *,
    structured_router: StructuredAgentRouter | None,
    fast_router: StructuredAgentRouter | None,
    compact_model: OpenAICompatibleHTTPChatModel | None,
) -> StrategyResult:
    started = time.perf_counter()
    error: str | None = None
    try:
        if strategy in ("baseline_fast_model", "baseline_0_8b"):
            assert structured_router is not None
            output = _from_agent_route(
                structured_router.route(
                    case.message,
                    case.route_context,
                    case.recent_messages or [],
                )
            )
        elif strategy == "fast_model":
            assert fast_router is not None
            output = _from_agent_route(
                fast_router.route(case.message, case.route_context, case.recent_messages or [])
            )
        elif strategy == "deterministic":
            output = deterministic_content_route(case)
        elif strategy == "deterministic_compact":
            output = deterministic_content_route(case)
            if output.intent == "clarify" and output.confidence < 0.65:
                assert compact_model is not None
                output = compact_router_route(case, compact_model)
        elif strategy == "content_fastpath_compact":
            output = deterministic_content_fast_path(case)
            if output is None:
                assert compact_model is not None
                output = compact_router_route(case, compact_model)
        elif strategy == "compact_all":
            assert compact_model is not None
            output = compact_router_route(case, compact_model)
        elif strategy == "compact_labeled_all":
            assert compact_model is not None
            output = compact_router_route(case, compact_model, labeled=True)
        elif strategy == "compact_decision_table_all":
            assert compact_model is not None
            output = compact_router_route(case, compact_model, variant="decision_table")
        elif strategy == "compact_fewshot_all":
            assert compact_model is not None
            output = compact_router_route(case, compact_model, variant="fewshot")
        elif strategy == "retrieval_first":
            output = deterministic_content_route(case)
            if output.intent == "clarify":
                output = CompactRouteOutput(
                    intent="find_content",
                    topic=case.active_topic or case.message,
                    confidence=0.7,
                    clarify=None,
                )
        elif strategy == "retrieval_first_compact":
            output = deterministic_content_fast_path(case)
            if output is None and case.route_context and case.route_context.get("retrieved_topic"):
                output = CompactRouteOutput(
                    intent="find_content",
                    topic=str(case.route_context["retrieved_topic"]),
                    confidence=0.75,
                    clarify=None,
                )
            if output is None:
                assert compact_model is not None
                output = compact_router_route(case, compact_model)
        elif strategy == "retrieval_first_labeled_compact":
            output = deterministic_content_fast_path(case)
            if output is None and case.route_context and case.route_context.get("retrieved_topic"):
                output = CompactRouteOutput(
                    intent="find_content",
                    topic=str(case.route_context["retrieved_topic"]),
                    confidence=0.75,
                    clarify=None,
                )
            if output is None:
                assert compact_model is not None
                output = compact_router_route(case, compact_model, labeled=True)
        else:
            raise ValueError(f"unknown strategy: {strategy}")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        output = CompactRouteOutput(intent="clarify", topic=None, confidence=0.0, clarify=error)

    latency_ms = (time.perf_counter() - started) * 1000
    quality = route_quality(case, output)
    return StrategyResult(
        strategy=strategy,
        case=case.name,
        latency_ms=latency_ms,
        intent=output.intent,
        topic=output.topic,
        confidence=output.confidence,
        clarify=output.clarify,
        intent_ok=quality["intent_ok"],
        topic_ok=quality["topic_ok"],
        score=quality["score"],
        error=error,
    )


async def run_benchmark(
    strategies: list[StrategyName],
    cases: list[BenchmarkCase],
    *,
    repeat: int,
) -> list[StrategyResult]:
    structured_router = build_production_agent_router() if "baseline_fast_model" in strategies else None
    guardrail_structured_router = (
        StructuredAgentRouter(model=_build_compact_router_model())
        if "baseline_0_8b" in strategies
        else None
    )
    fast_router = _build_fast_model_router() if "fast_model" in strategies else None
    needs_compact = needs_compact_model(strategies)
    compact_model = _build_compact_router_model() if needs_compact else None

    results: list[StrategyResult] = []
    for _ in range(repeat):
        for strategy in strategies:
            for case in cases:
                router = (
                    guardrail_structured_router
                    if strategy == "baseline_0_8b"
                    else structured_router
                )
                results.append(
                    await run_strategy_case(
                        strategy,
                        case,
                        structured_router=router,
                        fast_router=fast_router,
                        compact_model=compact_model,
                    )
                )
    return results


def summarize(results: list[StrategyResult]) -> list[dict[str, Any]]:
    rows = []
    for strategy in sorted({item.strategy for item in results}):
        items = [item for item in results if item.strategy == strategy]
        latencies = [item.latency_ms for item in items]
        rows.append(
            {
                "strategy": strategy,
                "cases": len(items),
                "avg_ms": round(statistics.mean(latencies), 1),
                "p50_ms": round(statistics.median(latencies), 1),
                "max_ms": round(max(latencies), 1),
                "quality": round(statistics.mean(item.score for item in items), 3),
                "errors": sum(1 for item in items if item.error),
            }
        )
    return rows


def print_summary(rows: list[dict[str, Any]]) -> None:
    headers = ["strategy", "cases", "avg_ms", "p50_ms", "max_ms", "quality", "errors"]
    print("\t".join(headers))
    for row in rows:
        print("\t".join(str(row[header]) for header in headers))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Agent router strategy variants.")
    parser.add_argument("--cases", default=None, help="Optional JSON case list.")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--strategies",
        default=",".join(default_strategy_names()),
    )
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]
    cases = load_cases(args.cases)
    results = asyncio.run(
        run_benchmark(strategies, cases, repeat=max(1, args.repeat))
    )
    rows = summarize(results)
    print_summary(rows)
    if args.output:
        Path(args.output).write_text(
            json.dumps(
                {
                    "summary": rows,
                    "results": [asdict(item) for item in results],
                    "chat_model_id": DEFAULT_CHAT_MODEL_ID,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
