from __future__ import annotations

from src.schemas.agent import AgentIntent
from src.services.agent_graph_contracts import AgentSlots, PolicyDecision


class AgentPolicyService:
    def evaluate(
        self,
        *,
        intent: AgentIntent,
        slots: AgentSlots,
        allowed_course_ids: list[str],
    ) -> PolicyDecision:
        if slots.course_ids:
            blocked = [course_id for course_id in slots.course_ids if course_id not in allowed_course_ids]
            if blocked:
                return PolicyDecision(
                    allow=False,
                    codes=["COURSE_SCOPE_MISMATCH"],
                    user_safe_message="That content is outside your allowed course scope.",
                    audit_context={"blockedCourseIds": blocked},
                )
        if intent == "request_path_switch" and not slots.target_path:
            return PolicyDecision(
                allow=False,
                codes=["TARGET_PATH_MISSING"],
                user_safe_message="Which path should I switch you to?",
            )
        return PolicyDecision(allow=True)
