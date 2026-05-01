"""
Deprecated compatibility service for pre-LangGraph tests and rollback.
Production /api/agent/chat requests must use AgentGraphService.
"""

from __future__ import annotations

import re
from uuid import uuid4

from src.schemas.agent import (
    AgentAction,
    AgentAnswer,
    AgentChatRequest,
    AgentChatResponse,
    AgentFallback,
    AgentIntent,
    AgentWarning,
    PathRequirementsRequest,
    RetrievalTrace,
    UnitSearchRequest,
)


INTENT_RULES: list[tuple[AgentIntent, tuple[str, ...]]] = [
    (
        "assess_knowledge",
        ("test me", "quiz me", "verify", "assessment", "can i skip", "skip", "already know", "i know"),
    ),
    (
        "explain_planner_decision",
        ("required for", "prerequisite", "prerequisites", "which dl parts", "need for nlp", "need before"),
    ),
    ("ask_what_next", ("what should i learn", "what next", "learn next", "study next", "before")),
    ("find_content", ("where is", "where can i review", "covered", "find", "open", "review")),
]


def classify_agent_intent(message: str, explicit_intent: AgentIntent | None = None) -> AgentIntent:
    if explicit_intent:
        return explicit_intent
    normalized = message.lower()
    for intent, phrases in INTENT_RULES:
        if any(phrase in normalized for phrase in phrases):
            return intent
    return "general_course_question"


def _has_any_phrase(normalized: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _has_any_token(normalized: str, tokens: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(token)}\b", normalized) for token in tokens)


def extract_requirement_target_path(message: str, route_context=None) -> str | None:
    normalized = message.lower()
    if _has_any_phrase(
        normalized,
        ("vision transformer", "computer vision", "cs231n", "cnn", "image"),
    ) or _has_any_token(normalized, ("vit", "cv")):
        return "computer_vision"
    if _has_any_phrase(
        normalized,
        ("natural language", "cs224n", "word vector", "transformer"),
    ) or _has_any_token(normalized, ("nlp",)):
        return "nlp"
    if route_context and getattr(route_context, "course_slug", None):
        course_slug = str(route_context.course_slug).lower()
        if course_slug == "cs224n":
            return "nlp"
        if course_slug == "cs231n":
            return "computer_vision"
    return None


class AgentChatService:
    def __init__(self, search_service, requirement_service):
        self.search_service = search_service
        self.requirement_service = requirement_service

    def _filter_trace(
        self,
        trace: RetrievalTrace,
        request: AgentChatRequest,
        is_reviewer: bool,
    ) -> RetrievalTrace | None:
        if request.trace_mode == "none":
            return None
        if request.trace_mode == "full" and not is_reviewer:
            return RetrievalTrace(
                trace_id=trace.trace_id,
                intent=trace.intent,
                raw_query=trace.raw_query,
                normalized_query=trace.normalized_query,
                resolved_scope=trace.resolved_scope,
                applied_filters=trace.applied_filters,
                ranking_version=trace.ranking_version,
                selected_unit_ids=trace.selected_unit_ids,
            )
        return trace

    async def chat(
        self,
        request: AgentChatRequest,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
        user_id: str | None = None,
        is_reviewer: bool = False,
    ) -> AgentChatResponse:
        intent = classify_agent_intent(request.message, request.intent)
        conversation_id = request.conversation_id or str(uuid4())

        if intent == "assess_knowledge":
            search = await self.search_service.search(
                UnitSearchRequest(query=request.message, scope="current_path", intent=intent, limit=12),
                allowed_course_ids=allowed_course_ids,
            )
            candidate_ids = [result.canonical_unit_id for result in search.results[:12]]
            return AgentChatResponse(
                conversation_id=conversation_id,
                message_id=str(uuid4()),
                answer=AgentAnswer(
                    markdown=(
                        "Self-report is not enough to update mastery. If you are ready, "
                        "I can prepare an assessment so the planner can use evidence."
                    ),
                    confidence="grounded",
                ),
                warning=AgentWarning(
                    type="needs_assessment",
                    message="Skipping requires assessment evidence. Self-report cannot update mastery by itself.",
                ),
                actions=[
                    AgentAction(
                        type="start_assessment_workflow",
                        label="Prepare assessment proposal",
                        canonical_unit_ids=candidate_ids,
                        default_phase="skip_verification",
                        eligible=bool(candidate_ids),
                        disabledReason=None if candidate_ids else "no_eligible_questions",
                    )
                ],
                trace=self._filter_trace(search.trace, request, is_reviewer),
            )

        if intent == "explain_planner_decision":
            target_path = extract_requirement_target_path(request.message, request.route_context)
            if target_path is None:
                return AgentChatResponse(
                    conversation_id=conversation_id,
                    message_id=str(uuid4()),
                    answer=AgentAnswer(
                        markdown="Which target path should I check prerequisites for: Computer Vision or NLP?",
                        confidence="partial",
                    ),
                    warning=AgentWarning(
                        type="ambiguous_target",
                        message="I need a target path before using the prerequisite graph reliably.",
                    ),
                    actions=[
                        AgentAction(type="choose_target_path", label="Computer Vision", eligible=True),
                        AgentAction(type="choose_target_path", label="NLP", eligible=True),
                    ],
                )
            requirements = await self.requirement_service.get_requirements(
                PathRequirementsRequest(targetPathKey=target_path),
                allowed_course_ids=allowed_course_ids,
                user_id=user_id,
            )
            citations = [
                {
                    "canonical_unit_id": unit.canonical_unit_id,
                    "course_id": unit.course_id,
                    "unit_name": unit.unit_name,
                    "learn_href": unit.learn_href,
                    "source": "planner",
                }
                for unit in requirements.required_units[:5]
            ]
            actions = [
                AgentAction(
                    type="open_unit",
                    label=f"Open {unit.unit_name}",
                    learn_href=unit.learn_href,
                    canonical_unit_id=unit.canonical_unit_id,
                )
                for unit in requirements.required_units[:3]
                if unit.learn_href
            ]
            answer = f"I checked the path requirement graph for {target_path.replace('_', ' ')} prerequisites."
            if not requirements.required_units:
                answer = "I could not find required prerequisite units in the current scoped path."
            return AgentChatResponse(
                conversation_id=conversation_id,
                message_id=str(uuid4()),
                answer=AgentAnswer(
                    markdown=answer,
                    confidence="grounded" if requirements.required_units else "no_source",
                ),
                citations=citations,
                actions=actions,
                trace=self._filter_trace(requirements.trace, request, is_reviewer),
            )

        search = await self.search_service.search(
            UnitSearchRequest(query=request.message, scope="current_path", intent=intent),
            allowed_course_ids=allowed_course_ids,
        )
        citations = []
        actions = []
        outside_current_path = False
        current_path = {course_id.lower() for course_id in (current_path_course_ids or allowed_course_ids)}
        for result in search.results[:3]:
            result_outside_path = result.course_id.lower() not in current_path
            outside_current_path = outside_current_path or result_outside_path
            citations.append(
                {
                    "canonical_unit_id": result.canonical_unit_id,
                    "course_id": result.course_id,
                    "lecture_id": result.lecture_id,
                    "lecture_title": result.lecture_title,
                    "unit_name": result.unit_name,
                    "learn_href": result.learn_href,
                    "quote": result.summary,
                    "source": "summary",
                }
            )
            if result.learn_href:
                actions.append(
                    AgentAction(
                        type="open_unit",
                        label=f"Open {result.unit_name}",
                        learn_href=result.learn_href,
                        canonical_unit_id=result.canonical_unit_id,
                    )
                )

        warning = None
        if outside_current_path:
            warning = AgentWarning(
                type="outside_current_path",
                message="At least one cited unit is outside your current path, but it is inside the controlled course catalog.",
            )

        return AgentChatResponse(
            conversation_id=conversation_id,
            message_id=str(uuid4()),
            answer=AgentAnswer(
                markdown="I found relevant learning units." if citations else "I could not find a grounded source.",
                confidence="grounded" if citations else "no_source",
            ),
            citations=citations,
            actions=actions,
            warning=warning,
            fallback=None
            if citations
            else AgentFallback(
                reason="no_retrieval_result",
                message="No grounded unit matched the query in your current scope.",
            ),
            trace=self._filter_trace(search.trace, request, is_reviewer),
        )
