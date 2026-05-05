from __future__ import annotations

from src.schemas.agent import AgentIntent, RouteContext
from src.services.agent_graph_contracts import AgentRoute, AgentSlots


class DeterministicAgentRouter:
    """Test/integration router only. Do not use as the production router."""

    def route(self, message: str, route_context: RouteContext | None) -> AgentRoute:
        text = message.lower().strip()
        intent: AgentIntent = "general_course_question"
        raw_topic: str | None = message.strip() or None
        target_path: str | None = None

        if text in {"ok", "yes", "approve", "được", "duoc"}:
            intent = "clarify"
            raw_topic = None
        elif "chuyển" in text or "doi path" in text or "đổi path" in text or "switch" in text:
            intent = "request_path_switch"
        elif "quiz" in text or "test me" in text or "kiểm tra" in text:
            if "eligibility" in text or "tính thế nào" in text:
                intent = "general_course_question"
            else:
                intent = "assess_knowledge"
        elif "where" in text or "tìm" in text or "ở đâu" in text:
            intent = "find_content"
        elif "explain" in text or "giải thích" in text:
            intent = "explain_concept"
        elif (
            "replan" in text
            or "tính lại lộ trình" in text
            or "tối ưu" in text and "lộ trình" in text
            or "optimize" in text and ("path" in text or "plan" in text)
        ):
            intent = "request_replan"

        if "nlp" in text or "cs224n" in text:
            target_path = "nlp"
        elif "cv" in text or "computer vision" in text or "cs231n" in text:
            target_path = "computer_vision"
        elif route_context and route_context.course_slug:
            slug = route_context.course_slug.lower()
            if slug == "cs224n":
                target_path = "nlp"
            elif slug == "cs231n":
                target_path = "computer_vision"

        search_scope = "explicit_path" if target_path and intent != "request_path_switch" else "current_path"
        return AgentRoute(
            intent=intent,
            confidence=0.75 if intent != "clarify" else 0.4,
            extracted_slots=AgentSlots(
                raw_topic=raw_topic,
                target_path=target_path,
                requested_path_id=target_path if search_scope == "explicit_path" else None,
                resolved_search_path_ids=[target_path] if search_scope == "explicit_path" else [],
                search_scope=search_scope,
            ),
            rationale="deterministic_test_router",
        )
