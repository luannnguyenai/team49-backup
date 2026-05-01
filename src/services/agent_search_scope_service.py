from __future__ import annotations

from src.services.agent_graph_contracts import AgentSlots, PendingClarification


PATH_COURSE_IDS: dict[str, list[str]] = {
    "computer_vision": ["CS230", "CS231n"],
    "nlp": ["CS230", "CS224n"],
}

PATH_LABELS: dict[str, str] = {
    "computer_vision": "Computer Vision",
    "nlp": "NLP",
}

APPROVAL_PHRASES = {"ok", "yes", "approve", "được", "duoc"}
REJECTION_PHRASES = {"no", "nope", "cancel", "không", "khong", "thôi", "thoi"}


class AgentSearchScopeService:
    def resolve_initial_scope(self, slots: AgentSlots, current_path_ids: list[str]) -> AgentSlots:
        if slots.search_scope != "current_path" and slots.resolved_search_path_ids:
            return slots
        if slots.requested_path_id:
            return slots.model_copy(
                update={
                    "search_scope": "explicit_path",
                    "resolved_search_path_ids": [slots.requested_path_id],
                }
            )
        return slots.model_copy(
            update={
                "search_scope": "current_path",
                "resolved_search_path_ids": current_path_ids,
            }
        )

    def offer_expansion_if_no_results(
        self,
        slots: AgentSlots,
        current_path_result_count: int,
        allowed_path_ids: list[str],
    ) -> AgentSlots:
        if slots.search_scope != "current_path" or current_path_result_count > 0:
            return slots
        if len(allowed_path_ids) <= len(slots.resolved_search_path_ids):
            return slots
        return slots.model_copy(update={"scope_expansion_offered": True})

    def approve_expansion(self, slots: AgentSlots, allowed_path_ids: list[str]) -> AgentSlots:
        return slots.model_copy(
            update={
                "scope_expansion_approved": True,
                "search_scope": "expanded_paths",
                "resolved_search_path_ids": allowed_path_ids,
            }
        )

    def path_ids_for_courses(self, course_ids: list[str]) -> list[str]:
        selected = set(course_ids)
        path_ids = [
            path_id
            for path_id, mapped_courses in PATH_COURSE_IDS.items()
            if selected.intersection(mapped_courses)
        ]
        return path_ids or ["computer_vision"]

    def course_ids_for_paths(self, path_ids: list[str], allowed_course_ids: list[str]) -> list[str]:
        allowed = set(allowed_course_ids)
        courses: list[str] = []
        for path_id in path_ids:
            for course_id in PATH_COURSE_IDS.get(path_id, []):
                if course_id in allowed and course_id not in courses:
                    courses.append(course_id)
        return courses or allowed_course_ids

    def path_ids_for_course(self, course_id: str, allowed_path_ids: list[str]) -> list[str]:
        allowed_paths = set(allowed_path_ids)
        return [
            path_id
            for path_id, course_ids in PATH_COURSE_IDS.items()
            if path_id in allowed_paths and course_id in course_ids
        ]

    def path_label(self, path_id: str) -> str:
        return PATH_LABELS.get(path_id, path_id.replace("_", " ").title())

    def is_scope_expansion_approval(
        self,
        message: str,
        pending: PendingClarification | None,
    ) -> bool:
        if pending is None or pending.type != "search_scope_expansion":
            return False
        normalized = message.lower().strip()
        return (
            normalized in APPROVAL_PHRASES
            or ("yes" in normalized and ("other path" in normalized or "other paths" in normalized))
            or "search other path" in normalized
            or "search other paths" in normalized
            or "mở rộng" in normalized
            or "mo rong" in normalized
            or "path khác" in normalized
            or "path khac" in normalized
        )

    def is_scope_expansion_rejection(
        self,
        message: str,
        pending: PendingClarification | None,
    ) -> bool:
        if pending is None or pending.type != "search_scope_expansion":
            return False
        normalized = message.lower().strip()
        return (
            normalized in REJECTION_PHRASES
            or normalized.startswith("no,")
            or normalized.startswith("no ")
            or "keep current path" in normalized
            or "current path only" in normalized
            or "không mở rộng" in normalized
            or "khong mo rong" in normalized
        )
