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
    def __init__(self, prerequisite_edges: dict[str, list[str]]) -> None:
        self.prerequisite_edges = prerequisite_edges

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
                suggestion = ReplanPrerequisiteSuggestion(
                    canonical_unit_id=unit.canonical_unit_id,
                    title=unit.title,
                    suggested_for_canonical_unit_id=root_id,
                    depth=depth,
                    path_order=unit.path_order,
                    reason=f"{unit.title} is a prerequisite for {root_id}.",
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

    @staticmethod
    def _eligible(unit: ReplanPrerequisiteUnit) -> bool:
        return unit.in_current_path and not unit.already_handled and unit.question_count > 0
