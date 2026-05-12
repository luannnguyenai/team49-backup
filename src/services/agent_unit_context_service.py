from __future__ import annotations

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import TranscriptSnippet, UnitContextResponse
from src.services.agent_navigation_service import AgentNavigationService


class AgentUnitContextService:
    def __init__(
        self,
        repo: CanonicalContentRepository,
        navigation_service: AgentNavigationService | None = None,
    ):
        self.repo = repo
        self.navigation_service = navigation_service or AgentNavigationService(repo)

    async def get_context(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str] | None = None,
    ) -> UnitContextResponse:
        units = await self.repo.get_canonical_units_by_ids([canonical_unit_id])
        unit = units.get(canonical_unit_id)
        if not unit:
            raise ValueError("unit_not_found")
        if allowed_course_ids is not None and unit.course_id not in allowed_course_ids:
            raise PermissionError("unit_out_of_scope")
        kp_rows = await self.repo.get_unit_kp_rows([canonical_unit_id])
        quiz_counts = await self.repo.get_quiz_item_counts_by_unit_ids([canonical_unit_id])
        nav = (await self.navigation_service.resolve_many([canonical_unit_id])).get(
            canonical_unit_id
        )
        snippets = await self.get_transcript_snippets(
            canonical_unit_id,
            allowed_course_ids=allowed_course_ids,
        )
        return UnitContextResponse(
            canonical_unit_id=canonical_unit_id,
            course_id=unit.course_id,
            unit_name=unit.unit_name,
            summary=unit.summary or unit.description,
            key_points=unit.key_points or [],
            kp_ids=[row.kp_id for row in kp_rows],
            quiz_available=quiz_counts.get(canonical_unit_id, 0) > 0 or bool(unit.has_quiz_items),
            learn_href=nav.learn_href if nav else None,
            transcript_snippets=[snippet.model_dump() for snippet in snippets],
        )

    async def get_transcript_snippets(
        self,
        canonical_unit_id: str,
        allowed_course_ids: list[str] | None = None,
        limit: int = 3,
    ) -> list[TranscriptSnippet]:
        units = await self.repo.get_canonical_units_by_ids([canonical_unit_id])
        unit = units.get(canonical_unit_id)
        if not unit:
            raise ValueError("unit_not_found")
        if allowed_course_ids is not None and unit.course_id not in allowed_course_ids:
            raise PermissionError("unit_out_of_scope")
        text = unit.summary or unit.description or unit.unit_name
        return [
            TranscriptSnippet(
                canonical_unit_id=canonical_unit_id,
                text=text,
                start_sec=None,
                end_sec=None,
            )
        ][:limit]
