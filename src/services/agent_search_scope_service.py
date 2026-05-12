from __future__ import annotations

from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_path_catalog import AGENT_PATH_CATALOG, fallback_path_label


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
            for path_id, entry in AGENT_PATH_CATALOG.items()
            if selected.intersection(entry.selected_course_ids)
        ]
        return path_ids or ["computer_vision"]

    def course_ids_for_paths(self, path_ids: list[str], allowed_course_ids: list[str]) -> list[str]:
        allowed = set(allowed_course_ids)
        courses: list[str] = []
        for path_id in path_ids:
            entry = AGENT_PATH_CATALOG.get(path_id)
            if entry is None:
                continue
            for course_id in entry.selected_course_ids:
                if course_id in allowed and course_id not in courses:
                    courses.append(course_id)
        return courses or allowed_course_ids

    def path_ids_for_course(self, course_id: str, allowed_path_ids: list[str]) -> list[str]:
        allowed_paths = set(allowed_path_ids)
        return [
            path_id
            for path_id, entry in AGENT_PATH_CATALOG.items()
            if path_id in allowed_paths and course_id in entry.selected_course_ids
        ]

    def path_label(self, path_id: str) -> str:
        entry = AGENT_PATH_CATALOG.get(path_id)
        return entry.label if entry is not None else fallback_path_label(path_id)
