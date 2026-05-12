from __future__ import annotations

from uuid import uuid4

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    PathRequirementsRequest,
    PathRequirementsResponse,
    PathRequirementUnit,
    RetrievalTrace,
)
from src.services.agent_navigation_service import AgentNavigationService

PATH_COURSES = {
    "computer_vision": ["CS231n"],
    "nlp": ["CS224n"],
}


class AgentPathRequirementService:
    def __init__(
        self,
        repo: CanonicalContentRepository,
        navigation_service: AgentNavigationService | None = None,
    ):
        self.repo = repo
        self.navigation_service = navigation_service or AgentNavigationService(repo)

    async def get_requirements(
        self,
        request: PathRequirementsRequest,
        allowed_course_ids: list[str],
        user_id=None,
    ) -> PathRequirementsResponse:
        target_courses = request.target_course_ids or PATH_COURSES.get(
            request.target_path_key or "", []
        )
        target_courses = [
            course_id for course_id in target_courses if course_id in allowed_course_ids
        ]
        target_units = await self.repo.search_canonical_units(
            [
                "foundation",
                "neural",
                "optimization",
                "embedding",
                "sequence",
                "cnn",
                "classification",
            ],
            target_courses,
            limit=40,
        )
        target_unit_ids = [unit.unit_id for unit in target_units]
        target_kp_rows = await self.repo.get_unit_kp_rows(target_unit_ids)
        target_kp_ids = sorted(
            {row.kp_id for row in target_kp_rows if row.planner_role in {"main", "prereq", None}}
        )
        edges = await self.repo.get_prerequisite_edges_for_kps(target_kp_ids)
        prereq_kp_ids = sorted(
            {edge.source_kp_id for edge in edges if edge.target_kp_id in target_kp_ids}
        )
        candidate_rows = (
            await self.repo.get_unit_kp_rows_by_kp_ids(prereq_kp_ids)
            if hasattr(self.repo, "get_unit_kp_rows_by_kp_ids")
            else []
        )
        if not candidate_rows:
            candidate_rows = await self.repo.get_unit_kp_rows(target_unit_ids)

        candidate_unit_ids = sorted({row.unit_id for row in candidate_rows})
        canonical_units = await self.repo.get_canonical_units_by_ids(candidate_unit_ids)
        nav_by_id = await self.navigation_service.resolve_many(candidate_unit_ids)
        mastery_by_kp = {}
        if (
            request.include_mastery
            and user_id is not None
            and hasattr(self.repo, "get_mastery_lcb_by_kp_ids")
        ):
            mastery_by_kp = await self.repo.get_mastery_lcb_by_kp_ids(user_id, prereq_kp_ids)

        required_units: list[PathRequirementUnit] = []
        for unit_id in candidate_unit_ids[:20]:
            unit = canonical_units.get(unit_id)
            if not unit or unit.course_id not in allowed_course_ids:
                continue
            if not self._eligible_unit(unit):
                continue
            unit_kp_ids = [row.kp_id for row in candidate_rows if row.unit_id == unit_id]
            mastery_lcb = min(
                (mastery_by_kp.get(kp_id, 0.0) for kp_id in unit_kp_ids), default=None
            )
            status = (
                "already_mastered" if mastery_lcb is not None and mastery_lcb >= 0.8 else "unknown"
            )
            nav = nav_by_id.get(unit_id)
            required_units.append(
                PathRequirementUnit(
                    canonical_unit_id=unit_id,
                    course_id=unit.course_id,
                    unit_name=unit.unit_name,
                    learn_href=nav.learn_href if nav else None,
                    required_kp_ids=unit_kp_ids,
                    mastery_lcb=mastery_lcb,
                    status=status,
                    reason="Required by prerequisite graph or target path foundation.",
                )
            )

        trace = RetrievalTrace(
            trace_id=str(uuid4()),
            intent="explain_planner_decision",
            resolved_scope="current_path",
            selected_path=request.target_path_key,
            candidate_courses=target_courses,
            applied_filters=["planner_role_main_or_prereq", "content_policy_core"],
            ranking_version="path_requirements_v1",
            runtime_navigation_resolution=[
                self.navigation_service.to_trace(nav_by_id[unit.canonical_unit_id])
                for unit in required_units
                if unit.canonical_unit_id in nav_by_id
            ],
            selected_unit_ids=[unit.canonical_unit_id for unit in required_units],
        )
        return PathRequirementsResponse(
            target_path_key=request.target_path_key,
            required_units=required_units,
            trace=trace,
        )

    @staticmethod
    def _eligible_unit(unit) -> bool:
        active = getattr(unit, "active", True)
        if active is False:
            return False
        flags = set(getattr(unit, "section_flags", None) or [])
        if flags.intersection({"logistics", "admin", "career", "history"}):
            return False
        content_type = getattr(unit, "content_type", None)
        if content_type in {"logistics", "reference"}:
            return False
        worth = getattr(unit, "is_worth_learning", None)
        return worth is not False
