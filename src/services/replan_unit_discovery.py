from __future__ import annotations

import logging
import re

from pydantic import BaseModel, ConfigDict, Field

from src.services.replan_keyword_planner import ReplanKeywordPlan

log = logging.getLogger(__name__)


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
        primary_terms = [_normalize(keyword.text) for keyword in plan.primary_keywords]
        forbidden_terms = {_normalize(term) for term in plan.do_not_expand_to}

        # DEBUG: Log keywords and match process
        log.info(f"[Replan Discovery] Primary terms: {primary_terms}")
        log.info(f"[Replan Discovery] Forbidden terms: {forbidden_terms}")

        for candidate in candidates:
            if not candidate.in_current_path:
                result.dropped_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Unit is outside the current path.",
                    ),
                )
                continue

            title = _normalize(candidate.title)
            summary = _normalize(candidate.summary)
            key_points = [_normalize(kp) for kp in candidate.key_points]
            haystack = _normalize(" ".join([candidate.title, candidate.summary, *candidate.key_points]))

            match_score = 0
            matched_terms = []

            for term in primary_terms:
                if not term:
                    continue
                if _phrase_in_text(term, title):
                    match_score += 25 if term == title else 20
                    matched_terms.append(f"{term}(title)")
                elif any(_phrase_in_text(term, kp) for kp in key_points):
                    match_score += 15
                    matched_terms.append(f"{term}(kp)")
                elif _phrase_in_text(term, summary):
                    match_score += 10
                    matched_terms.append(f"{term}(summary)")

            if title in forbidden_terms and match_score < 25:
                result.excluded_units.append(
                    ReplanExcludedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason="Matched only a forbidden expansion keyword.",
                    ),
                )
                continue

            MIN_SCORE = 15
            if match_score >= MIN_SCORE:
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
                log.info(f"[Replan Discovery] SELECTED: {candidate.title} (score: {match_score}, matches: {matched_terms})")
                result.selected_units.append(
                    ReplanSelectedUnit(
                        canonical_unit_id=candidate.canonical_unit_id,
                        reason=f"Matched: {', '.join(matched_terms)}",
                    ),
                )
                continue
            else:
                if matched_terms:
                    log.debug(f"[Replan Discovery] SKIPPED (low score {match_score} < {MIN_SCORE}): {candidate.title} (matches: {matched_terms})")
                else:
                    log.debug(f"[Replan Discovery] SKIPPED (no match): {candidate.title}")

            if title in forbidden_terms:
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


def _normalize(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(normalized.split())


def _phrase_in_text(term: str, text: str) -> bool:
    if not term or not text:
        return False
    padded_text = f" {text} "
    return any(f" {variant} " in padded_text for variant in _phrase_variants(term))


def _phrase_variants(term: str) -> set[str]:
    tokens = term.split()
    variants = {term}
    for index, token in enumerate(tokens):
        if len(token) <= 3:
            continue
        replacement = token[:-1] if token.endswith("s") else f"{token}s"
        if len(replacement) <= 3:
            continue
        next_tokens = list(tokens)
        next_tokens[index] = replacement
        variants.add(" ".join(next_tokens))
    return variants
