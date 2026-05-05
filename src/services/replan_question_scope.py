from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Difficulty = Literal["easy", "medium", "hard", "application"]


class ReplanScopeUnit(BaseModel):
    canonical_unit_id: str = Field(alias="canonicalUnitId")
    title: str
    source: Literal["matched_from_description", "suggested_prerequisite"]
    suggested_for_title: str | None = Field(default=None, alias="suggestedForTitle")
    key_points: list[str] = Field(default_factory=list, alias="keyPoints")

    model_config = ConfigDict(populate_by_name=True)


class ReplanQuestion(BaseModel):
    unit_id: str = Field(alias="unitId")
    difficulty: Difficulty
    knowledge_points: list[str] = Field(default_factory=list, alias="knowledgePoints")

    model_config = ConfigDict(populate_by_name=True)


class ReplanReviewScopeUnit(BaseModel):
    canonical_unit_id: str
    title: str
    source: Literal["matched_from_description", "suggested_prerequisite"]
    suggested_for_title: str | None = None
    knowledge_points: list[str]
    question_counts: dict[Difficulty, int]


class ReplanQuestionScopeBuilder:
    def build(
        self,
        units: list[ReplanScopeUnit],
        questions: list[ReplanQuestion],
        unit_kp_map: dict[str, list[str]],
    ) -> list[ReplanReviewScopeUnit]:
        questions_by_unit: dict[str, list[ReplanQuestion]] = {}
        for question in questions:
            questions_by_unit.setdefault(question.unit_id, []).append(question)

        return [
            ReplanReviewScopeUnit(
                canonical_unit_id=unit.canonical_unit_id,
                title=unit.title,
                source=unit.source,
                suggested_for_title=unit.suggested_for_title,
                knowledge_points=self._knowledge_points(
                    questions_by_unit.get(unit.canonical_unit_id, []),
                    unit_kp_map.get(unit.canonical_unit_id, []),
                    unit.key_points,
                ),
                question_counts=self._question_counts(questions_by_unit.get(unit.canonical_unit_id, [])),
            )
            for unit in units
        ]

    @staticmethod
    def _knowledge_points(
        questions: list[ReplanQuestion],
        mapped_points: list[str],
        canonical_points: list[str],
    ) -> list[str]:
        question_points = _dedupe(
            point
            for question in questions
            for point in question.knowledge_points
            if point
        )
        if question_points:
            return question_points
        if mapped_points:
            return _dedupe(mapped_points)
        return _dedupe(canonical_points)

    @staticmethod
    def _question_counts(questions: list[ReplanQuestion]) -> dict[Difficulty, int]:
        counts: dict[Difficulty, int] = {"easy": 0, "medium": 0, "hard": 0, "application": 0}
        for question in questions:
            counts[question.difficulty] += 1
        return counts


def _dedupe(points: list[str] | object) -> list[str]:
    seen = set()
    result = []
    for point in points:
        if point not in seen:
            seen.add(point)
            result.append(point)
    return result
