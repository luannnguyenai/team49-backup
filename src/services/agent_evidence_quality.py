from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from src.schemas.agent import UnitSearchResult


EvidenceLabel = Literal["direct_match", "related_match", "weak_match", "no_match"]


@dataclass(frozen=True)
class EvidenceQualityVerdict:
    label: EvidenceLabel
    selected_unit_ids: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    match_reasons: dict[str, str] = field(default_factory=dict)

    @property
    def requires_grounded_answer(self) -> bool:
        return self.label == "direct_match"


class AgentEvidenceQualityService:
    MAX_EVIDENCE_CANDIDATES = 100

    def score(self, query: str, results: list[UnitSearchResult]) -> EvidenceQualityVerdict:
        positive_results = [result for result in results if result.score > 0]
        if not positive_results:
            return EvidenceQualityVerdict(label="no_match", reason_codes=["no_positive_score"])

        query_terms = self._terms(query)
        if not query_terms:
            return EvidenceQualityVerdict(
                label="weak_match",
                selected_unit_ids=[result.canonical_unit_id for result in positive_results[:3]],
                reason_codes=["empty_query_terms"],
            )
        acronym_terms = self._acronym_terms(query)

        match_reasons: dict[str, str] = {}
        direct_matches: list[tuple[float, float, int, str]] = []
        related_matches: list[tuple[float, float, int, str]] = []
        for index, result in enumerate(positive_results[: self.MAX_EVIDENCE_CANDIDATES]):
            title_text = " ".join(
                [
                    result.unit_name or "",
                    result.lecture_title or "",
                ]
            )
            body_text = " ".join(
                [
                    result.summary or "",
                    result.unit_name or "",
                    result.lecture_title or "",
                ]
            )
            title_coverage = self._coverage(query_terms, title_text)
            body_coverage = self._coverage(query_terms, body_text)
            acronym_match = bool(
                acronym_terms
                and (
                    self._coverage(acronym_terms, title_text) > 0
                    or self._coverage(acronym_terms, body_text) > 0
                )
            )
            title_direct = self._has_phrase_match(query_terms, title_text) or title_coverage >= 0.75
            body_direct = len(query_terms) > 1 and body_coverage >= 0.85
            if acronym_match or title_direct or body_direct:
                direct_matches.append(
                    (title_coverage, body_coverage, index, result.canonical_unit_id)
                )
                match_reasons[result.canonical_unit_id] = (
                    "Explicit acronym match."
                    if acronym_match
                    else "Strong title, lecture, or summary coverage."
                )
            elif body_coverage >= 0.35 or result.score >= 2:
                related_matches.append(
                    (title_coverage, body_coverage, index, result.canonical_unit_id)
                )
                match_reasons[result.canonical_unit_id] = "Related result with partial topic overlap."

        if direct_matches:
            direct_matches.sort(key=lambda item: (-item[0], -item[1], item[2]))
            return EvidenceQualityVerdict(
                label="direct_match",
                selected_unit_ids=[item[3] for item in direct_matches[:3]],
                reason_codes=["title_or_lecture_match"],
                match_reasons=match_reasons,
            )
        if related_matches:
            related_matches.sort(key=lambda item: (-item[0], -item[1], item[2]))
            return EvidenceQualityVerdict(
                label="related_match",
                selected_unit_ids=[item[3] for item in related_matches[:3]],
                reason_codes=["summary_partial_match"],
                match_reasons=match_reasons,
            )
        return EvidenceQualityVerdict(
            label="weak_match",
            selected_unit_ids=[result.canonical_unit_id for result in positive_results[:3]],
            reason_codes=["low_query_coverage"],
            match_reasons={
                result.canonical_unit_id: "Weak lexical overlap only."
                for result in positive_results[:3]
            },
        )

    def _terms(self, query: str) -> list[str]:
        terms = []
        for raw_term in re.findall(r"[a-zA-Z0-9]+", query):
            term = raw_term.lower()
            if len(term) <= 2:
                continue
            terms.append(self._normalize_term(term))
            if raw_term.endswith("s") and raw_term[:-1].isupper() and len(raw_term) > 2:
                terms.append(raw_term[:-1].lower())
        for compactable in re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)+", query.lower()):
            parts = [part for part in re.split(r"[-_]+", compactable) if part]
            compacted = re.sub(r"[^a-z0-9]+", "", compactable)
            if len(compacted) > 2:
                terms.append(self._normalize_term(compacted))
            if any(len(part) == 1 for part in parts):
                terms = [term for term in terms if term not in parts]
        return sorted(set(terms))

    def _acronym_terms(self, query: str) -> list[str]:
        return sorted(
            {
                raw_term.lower()
                for raw_term in re.findall(r"[A-Z][A-Z0-9]{2,}", query)
            }
        )

    def _coverage(self, terms: list[str], text: str) -> float:
        normalized = text.lower()
        if not terms:
            return 0.0
        matched = sum(1 for term in terms if self._term_in_text(term, normalized))
        return matched / len(terms)

    def _has_phrase_match(self, terms: list[str], text: str) -> bool:
        if len(terms) < 2:
            return False
        normalized = text.lower()
        return any(
            self._term_in_text(first, normalized) and self._term_in_text(second, normalized)
            for first, second in zip(terms, terms[1:])
        )

    def _normalize_term(self, term: str) -> str:
        if len(term) > 4 and term.endswith("s"):
            return term[:-1]
        return term

    def _term_in_text(self, term: str, text: str) -> bool:
        compact_text = re.sub(r"[-_]+", "", text.lower())
        compact_term = re.sub(r"[-_]+", "", term.lower())
        return term in text or bool(compact_term and compact_term in compact_text)
