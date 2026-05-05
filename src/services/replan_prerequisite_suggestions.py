from __future__ import annotations

from collections import deque

from pydantic import BaseModel, ConfigDict, Field


class ReplanPrerequisiteUnit(BaseModel):
    canonical_unit_id: str = Field(alias="canonicalUnitId")
    title: str
    path_order: int = Field(alias="pathOrder")
    in_current_path: bool = Field(default=True, alias="inCurrentPath")
    already_handled: bool = Field(default=False, alias="alreadyHandled")
    question_count: int = Field(default=0, alias="questionCount")

    model_config = ConfigDict(populate_by_name=True)


class ReplanPrerequisiteSuggestion(BaseModel):
    canonical_unit_id: str
    title: str
    suggested_for_canonical_unit_id: str
    depth: int
    path_order: int
    reason: str


class ReplanPrerequisiteSuggester:
    def __init__(
        self,
        prerequisite_edges: dict[str, list[str]],
        unit_kp_edges: dict[tuple[str, str], list[tuple[str, str]]] | None = None,
    ) -> None:
        """
        Args:
            prerequisite_edges: {unit_id -> [prerequisite_unit_ids]}
            unit_kp_edges: {(source_unit, target_unit) -> [(source_kp_name, target_kp_name), ...]}
        """
        self.prerequisite_edges = prerequisite_edges
        self.unit_kp_edges = unit_kp_edges or {}

    def suggest(
        self,
        selected_unit_ids: list[str],
        units_by_id: dict[str, ReplanPrerequisiteUnit],
        max_depth: int = 2,
        max_suggestions: int = 5,
    ) -> list[ReplanPrerequisiteSuggestion]:
        suggestions: dict[str, ReplanPrerequisiteSuggestion] = {}
        queue = deque(
            (selected_unit_id, selected_unit_id, prerequisite_id, 1)
            for selected_unit_id in selected_unit_ids
            for prerequisite_id in self.prerequisite_edges.get(selected_unit_id, [])
        )

        while queue:
            root_id, parent_id, prerequisite_id, depth = queue.popleft()
            if depth > max_depth:
                continue

            unit = units_by_id.get(prerequisite_id)
            if unit and self._eligible(unit):
                existing = suggestions.get(prerequisite_id)

                # Build reason with KP names if available
                reason = self._build_reason(prerequisite_id, root_id, units_by_id)

                suggestion = ReplanPrerequisiteSuggestion(
                    canonical_unit_id=unit.canonical_unit_id,
                    title=unit.title,
                    suggested_for_canonical_unit_id=root_id,
                    depth=depth,
                    path_order=unit.path_order,
                    reason=reason,
                )
                if existing is None or (suggestion.depth, suggestion.path_order) < (
                    existing.depth,
                    existing.path_order,
                ):
                    suggestions[prerequisite_id] = suggestion

            if depth < max_depth:
                queue.extend(
                    (root_id, prerequisite_id, next_id, depth + 1)
                    for next_id in self.prerequisite_edges.get(prerequisite_id, [])
                    if next_id != parent_id
                )

        ranked = sorted(
            suggestions.values(),
            key=lambda suggestion: (suggestion.depth, suggestion.path_order, suggestion.canonical_unit_id),
        )
        return ranked[:max_suggestions]

    def _build_reason(
        self,
        prereq_unit_id: str,
        target_unit_id: str,
        units_by_id: dict[str, ReplanPrerequisiteUnit],
    ) -> str:
        """Build reason string with KP names if available."""
        prereq_unit = units_by_id.get(prereq_unit_id)
        target_unit = units_by_id.get(target_unit_id)

        prereq_title = prereq_unit.title if prereq_unit else prereq_unit_id
        target_title = target_unit.title if target_unit else target_unit_id

        # Check if we have KP-level edges for this unit pair
        kp_edges = self.unit_kp_edges.get((prereq_unit_id, target_unit_id), [])

        if not kp_edges:
            # Fallback to unit-level reason
            return f"{prereq_title} is a prerequisite for {target_title}."

        # Build reason with specific KP pairs
        # Show up to 2 KP pairs to keep it concise
        shown_kp_pairs = kp_edges[:2]
        kp_reasons = [
            f"{source_kp} → {target_kp}"
            for source_kp, target_kp in shown_kp_pairs
        ]

        if len(kp_edges) > 2:
            kp_reasons.append(f"and {len(kp_edges) - 2} more")

        return f"Prerequisite: {', '.join(kp_reasons)}."

    @staticmethod
    def _eligible(unit: ReplanPrerequisiteUnit) -> bool:
        return unit.in_current_path and not unit.already_handled and unit.question_count > 0
