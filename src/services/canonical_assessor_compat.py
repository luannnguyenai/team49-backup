import uuid
from typing import Any

from src.models.content import BloomLevel, CorrectAnswer, DifficultyBucket
from src.schemas.module_test import QuestionForModuleTest
from src.schemas.quiz import QuestionForQuiz


_CANONICAL_QUESTION_UUID_NAMESPACE = uuid.UUID("6bf5d76f-fab9-48d4-903e-d0fd13a7d767")
_ANSWER_BY_INDEX = {
    0: CorrectAnswer.A,
    1: CorrectAnswer.B,
    2: CorrectAnswer.C,
    3: CorrectAnswer.D,
}
_INDEX_BY_ANSWER = {answer.value: index for index, answer in _ANSWER_BY_INDEX.items()}
_INTENT_TO_BLOOM = {
    "conceptual": BloomLevel.understand,
    "procedural": BloomLevel.apply,
    "application": BloomLevel.apply,
    "diagnostic": BloomLevel.analyze,
}


def canonical_question_uuid(item_id: str) -> uuid.UUID:
    """Stable surrogate UUID for legacy frontend payloads keyed by canonical item_id."""
    return uuid.uuid5(_CANONICAL_QUESTION_UUID_NAMESPACE, item_id)


def answer_index_to_correct_answer(answer_index: int) -> CorrectAnswer:
    return _ANSWER_BY_INDEX.get(answer_index, CorrectAnswer.A)


def selected_answer_to_index(selected_answer: str) -> int:
    return _INDEX_BY_ANSWER[str(selected_answer)]


def canonical_item_to_quiz_question(item: Any, *, topic_id: uuid.UUID) -> QuestionForQuiz:
    return QuestionForQuiz(
        id=canonical_question_uuid(str(item.item_id)),
        item_id=str(item.item_id),
        topic_id=topic_id,
        bloom_level=_canonical_bloom_level(getattr(item, "question_intent", None)),
        difficulty_bucket=_canonical_difficulty(getattr(item, "difficulty", None)),
        stem_text=str(item.question),
        option_a=_choice(item, 0),
        option_b=_choice(item, 1),
        option_c=_choice(item, 2),
        option_d=_choice(item, 3),
        time_expected_seconds=None,
    )


def canonical_item_to_module_test_question(item: Any, *, topic_id: uuid.UUID) -> QuestionForModuleTest:
    return QuestionForModuleTest(
        id=canonical_question_uuid(str(item.item_id)),
        item_id=str(item.item_id),
        topic_id=topic_id,
        bloom_level=_canonical_bloom_level(getattr(item, "question_intent", None)),
        difficulty_bucket=_canonical_difficulty(getattr(item, "difficulty", None)),
        stem_text=str(item.question),
        option_a=_choice(item, 0),
        option_b=_choice(item, 1),
        option_c=_choice(item, 2),
        option_d=_choice(item, 3),
        time_expected_seconds=None,
    )


def _canonical_difficulty(value: str | None) -> DifficultyBucket:
    try:
        return DifficultyBucket(str(value or "medium").lower())
    except ValueError:
        return DifficultyBucket.medium


def _canonical_bloom_level(value: str | None) -> BloomLevel:
    return _INTENT_TO_BLOOM.get(str(value or "").lower(), BloomLevel.understand)


def _choice(item: Any, index: int) -> str:
    choices = list(getattr(item, "choices", []) or [])
    if index >= len(choices):
        return ""
    choice = choices[index]
    if isinstance(choice, dict):
        return str(choice.get("text") or "")
    return str(choice)
