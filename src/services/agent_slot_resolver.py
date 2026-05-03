from __future__ import annotations

from src.schemas.agent import AgentIntent, UnitSearchRequest
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_search_scope_service import AgentSearchScopeService


class AgentSlotResolver:
    def __init__(self, search_service, scope_service: AgentSearchScopeService | None = None):
        self.search_service = search_service
        self.scope_service = scope_service or AgentSearchScopeService()

    async def canonicalize(
        self,
        *,
        raw_slots: AgentSlots,
        intent: AgentIntent,
        allowed_course_ids: list[str],
        current_path_course_ids: list[str] | None = None,
    ) -> AgentSlots:
        current_path_ids = self.scope_service.path_ids_for_courses(
            current_path_course_ids or allowed_course_ids
        )
        slots = self.scope_service.resolve_initial_scope(raw_slots, current_path_ids)
        if slots.canonical_unit_ids or intent != "assess_knowledge":
            return slots

        query = slots.raw_topic or ""
        if not query.strip():
            return slots

        search_courses = self.scope_service.course_ids_for_paths(
            slots.resolved_search_path_ids,
            allowed_course_ids,
        )
        search = await self.search_service.search(
            UnitSearchRequest(query=query, courseIds=search_courses, intent=intent, limit=5),
            allowed_course_ids=allowed_course_ids,
        )
        matches = [result for result in search.results if result.score > 0]
        if not matches:
            return slots
        if len(matches) > 1 and matches[0].score == matches[1].score:
            return slots.model_copy(
                update={
                    "ambiguity_options": [
                        {
                            "canonical_unit_id": result.canonical_unit_id,
                            "course_id": result.course_id,
                            "unit_name": result.unit_name,
                        }
                        for result in matches[:5]
                    ]
                }
            )
        return slots.model_copy(
            update={
                "canonical_unit_ids": [matches[0].canonical_unit_id],
                "course_ids": [matches[0].course_id],
            }
        )
