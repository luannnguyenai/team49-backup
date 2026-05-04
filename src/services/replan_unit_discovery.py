from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.services.replan_keyword_planner import ReplanKeywordPlan


class ReplanUnitCandidate(BaseModel):
    canonical_unit_id: str = Field(alias="canonicalUnitId")
    title: str
    summary: str = ""
    key_points: list[str] = Field(default_factory=list, alias="keyPoints")
    path_order: int = Field(alias="pathOrder")
    question_counts: dict[str, int] = Field(alias="questionCounts")
    in_current_path: bool = Field(default=True, alias="inCurrentPath")
    already_handled: bool = Field(default=False, alias="alreadyHandled")

    model_config = ConfigDict(populate_by_name=True)


class ReplanSelectedUnit(BaseModel):
    canonical_unit_id: str
    selection: str = "include"
    reason: str


class ReplanExcludedUnit(BaseModel):
    canonical_unit_id: str
    reason: str


class ReplanUnitDiscoveryResult(BaseModel):
    selected_units: list[ReplanSelectedUnit] = Field(default_factory=list)
    excluded_units: list[ReplanExcludedUnit] = Field(default_factory=list)
    dropped_units: list[ReplanExcludedUnit] = Field(default_factory=list)
    maybe_units: list[ReplanExcludedUnit] = Field(default_factory=list)


class ReplanCurrentPathUnitDiscovery:
    def discover(
        self,
        plan: ReplanKeywordPlan,
        candidates: list[ReplanUnitCandidate],
    ) -> ReplanUnitDiscoveryResult:
        result = ReplanUnitDiscoveryResult()
        primary_terms = [keyword.text.casefold() for keyword in plan.primary_keywords]
        forbidden_terms = {term.casefold() for term in plan.do_not_expand_to}

        for candidate in candidates:
            if not candidate.in_current_path:
                result.dropped_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Unit is outside the current path.",
                    ),
                )
                continue
            if sum(candidate.question_counts.values()) <= 0:
                result.dropped_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="No assessment questions available.",
                    ),
                )
                continue
            if candidate.already_handled:
                result.dropped_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Unit is already mastered or skipped.",
                    ),
                )
                continue

            haystack = " ".join([candidate.title, candidate.summary, *candidate.key_points]).casefold()
            if any(term in haystack for term in primary_terms):
                result.selected_units.append(
                    ReplanSelectedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Exact conceptual match to the user's claim.",
                    ),
                )
                continue

            title = candidate.title.casefold()
            if title in forbidden_terms or any(title == term for term in forbidden_terms):
                result.excluded_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Matched only a forbidden expansion keyword.",
                    ),
                )

        result.selected_units.sort(key=lambda unit: _path_order(unit.canonical_unit_id, candidates))
        return result


def _path_order(canonical_unit_id: str, candidates: list[ReplanUnitCandidate]) -> int:
    for candidate in candidates:
        if candidate.canonical_unit_id == canonical_unit_id:
            return candidate.path_order
    return 0
