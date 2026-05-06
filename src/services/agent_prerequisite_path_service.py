from __future__ import annotations

from collections import Counter, defaultdict
from uuid import UUID

from src.repositories.canonical_content_repo import CanonicalContentRepository
from src.schemas.agent import (
    AgentPrerequisitePath,
    AgentPrerequisitePathEdge,
    AgentPrerequisitePathNode,
)
from src.services.agent_navigation_service import AgentNavigationService


class AgentPrerequisitePathService:
    def __init__(
        self,
        repo: CanonicalContentRepository,
        navigation_service: AgentNavigationService | None = None,
    ):
        self.repo = repo
        self.navigation_service = navigation_service or AgentNavigationService(repo)

    async def build(
        self,
        *,
        target_canonical_unit_id: str,
        allowed_course_ids: list[str],
        user_id: UUID | None = None,
        max_prerequisite_units: int = 4,
    ) -> AgentPrerequisitePath | None:
        target_units = await self.repo.get_canonical_units_by_ids([target_canonical_unit_id])
        target_unit = target_units.get(target_canonical_unit_id)
        if target_unit is None or target_unit.course_id not in allowed_course_ids:
            return None

        target_kp_rows = await self.repo.get_unit_kp_rows([target_canonical_unit_id])
        target_kp_ids = sorted({row.kp_id for row in target_kp_rows})
        if not target_kp_ids:
            return None

        prerequisite_edges = [
            edge
            for edge in await self.repo.get_prerequisite_edges_for_kps(target_kp_ids)
            if getattr(edge, "active", True) and edge.target_kp_id in target_kp_ids
        ]
        prerequisite_kp_ids = sorted({edge.source_kp_id for edge in prerequisite_edges})
        if not prerequisite_kp_ids:
            return None

        candidate_rows = await self.repo.get_unit_kp_rows_by_kp_ids(prerequisite_kp_ids)
        candidate_unit_ids = sorted(
            {
                row.unit_id
                for row in candidate_rows
                if row.unit_id != target_canonical_unit_id
            }
        )
        if not candidate_unit_ids:
            return None

        unit_by_id = await self.repo.get_canonical_units_by_ids(
            [*candidate_unit_ids, target_canonical_unit_id]
        )
        candidate_unit_ids = [
            unit_id
            for unit_id in candidate_unit_ids
            if self._eligible_unit(unit_by_id.get(unit_id), allowed_course_ids)
        ]
        if not candidate_unit_ids:
            return None

        source_unit_by_kp: dict[str, set[str]] = defaultdict(set)
        for row in candidate_rows:
            if row.unit_id in candidate_unit_ids:
                source_unit_by_kp[row.kp_id].add(row.unit_id)

        edge_reasons_by_pair: dict[tuple[str, str], list[str]] = defaultdict(list)
        source_counts: Counter[str] = Counter()
        concept_by_id = await self.repo.get_concepts_by_ids(
            sorted({*prerequisite_kp_ids, *target_kp_ids})
        )
        for edge in prerequisite_edges:
            source_name = getattr(concept_by_id.get(edge.source_kp_id), "name", edge.source_kp_id)
            target_name = getattr(concept_by_id.get(edge.target_kp_id), "name", edge.target_kp_id)
            reason = f"{source_name} -> {target_name}"
            for source_unit_id in source_unit_by_kp.get(edge.source_kp_id, set()):
                source_counts[source_unit_id] += 1
                edge_reasons_by_pair[(source_unit_id, target_canonical_unit_id)].append(reason)

        ordered_prereq_ids = [
            unit_id
            for unit_id, _count in source_counts.most_common()
        ][:max_prerequisite_units]
        if not ordered_prereq_ids:
            return None

        ordered_unit_ids = [*ordered_prereq_ids, target_canonical_unit_id]
        nav_by_id = await self.navigation_service.resolve_many(ordered_unit_ids)
        status_by_unit = (
            await self.repo.get_user_learning_status_by_canonical_ids(user_id, ordered_unit_ids)
            if user_id is not None
            and hasattr(self.repo, "get_user_learning_status_by_canonical_ids")
            else {}
        )
        unit_kp_rows = await self.repo.get_unit_kp_rows(ordered_unit_ids)
        kp_ids_by_unit: dict[str, list[str]] = defaultdict(list)
        for row in unit_kp_rows:
            kp_ids_by_unit[row.unit_id].append(row.kp_id)
        mastery_by_kp = (
            await self.repo.get_mastery_lcb_by_kp_ids(
                user_id,
                sorted({kp_id for kp_ids in kp_ids_by_unit.values() for kp_id in kp_ids}),
            )
            if user_id is not None and hasattr(self.repo, "get_mastery_lcb_by_kp_ids")
            else {}
        )

        nodes: list[AgentPrerequisitePathNode] = []
        for unit_id in ordered_unit_ids:
            unit = unit_by_id.get(unit_id)
            if unit is None:
                continue
            role = "target" if unit_id == target_canonical_unit_id else "prerequisite"
            mastery_lcb = self._unit_mastery_lcb(kp_ids_by_unit.get(unit_id, []), mastery_by_kp)
            status = self._resolve_status(
                raw_status=status_by_unit.get(unit_id),
                mastery_lcb=mastery_lcb,
                role=role,
            )
            nav = nav_by_id.get(unit_id)
            nodes.append(
                AgentPrerequisitePathNode(
                    canonicalUnitId=unit_id,
                    unitName=unit.unit_name,
                    role=role,
                    status=status,
                    learnHref=nav.learn_href if nav else None,
                    masteryLcb=mastery_lcb,
                    reason=self._node_reason(status=status, role=role),
                )
            )

        edges = [
            AgentPrerequisitePathEdge(
                fromCanonicalUnitId=unit_id,
                toCanonicalUnitId=target_canonical_unit_id,
                reason="; ".join(edge_reasons_by_pair.get((unit_id, target_canonical_unit_id), [])[:2])
                or None,
            )
            for unit_id in ordered_prereq_ids
        ]
        return AgentPrerequisitePath(
            targetCanonicalUnitId=target_canonical_unit_id,
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _eligible_unit(unit, allowed_course_ids: list[str]) -> bool:
        if unit is None or unit.course_id not in allowed_course_ids:
            return False
        if getattr(unit, "active", True) is False:
            return False
        flags = set(getattr(unit, "section_flags", None) or [])
        if flags.intersection({"logistics", "admin", "career", "history"}):
            return False
        if getattr(unit, "content_type", None) in {"logistics", "reference"}:
            return False
        return getattr(unit, "is_worth_learning", None) is not False

    @staticmethod
    def _unit_mastery_lcb(kp_ids: list[str], mastery_by_kp: dict[str, float]) -> float | None:
        values = [mastery_by_kp[kp_id] for kp_id in kp_ids if kp_id in mastery_by_kp]
        return min(values) if values else None

    @staticmethod
    def _resolve_status(*, raw_status: str | None, mastery_lcb: float | None, role: str) -> str:
        if raw_status in {"skipped", "completed", "in_progress"}:
            return raw_status
        if mastery_lcb is not None and mastery_lcb >= 0.8:
            return "mastered"
        if role == "target" and raw_status in {None, "not_started"}:
            return "target"
        return "needs_review"

    @staticmethod
    def _node_reason(*, status: str, role: str) -> str | None:
        if role == "target":
            return "Current topic."
        if status in {"skipped", "completed", "mastered"}:
            return "Already handled; included so the learning order is clear."
        return "Review this first to make the target topic easier."
