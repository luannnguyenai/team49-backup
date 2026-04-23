from types import SimpleNamespace
import uuid

from src.models.content import CorrectAnswer, DifficultyBucket
from src.services.canonical_assessor_compat import (
    answer_index_to_correct_answer,
    canonical_item_to_quiz_question,
    canonical_question_uuid,
    selected_answer_to_index,
)


def test_canonical_question_uuid_is_stable_for_item_id():
    assert canonical_question_uuid("item-1") == canonical_question_uuid("item-1")
    assert canonical_question_uuid("item-1") != canonical_question_uuid("item-2")


def test_answer_index_and_selected_answer_mapping():
    assert answer_index_to_correct_answer(0) == CorrectAnswer.A
    assert answer_index_to_correct_answer(3) == CorrectAnswer.D
    assert selected_answer_to_index("C") == 2


def test_canonical_item_to_quiz_question_preserves_frontend_shape():
    topic_id = uuid.uuid4()
    item = SimpleNamespace(
        item_id="item-1",
        question="What is attention?",
        choices=["A", "B", "C", "D"],
        difficulty="easy",
        question_intent="conceptual",
    )

    payload = canonical_item_to_quiz_question(item, topic_id=topic_id)

    assert payload.id == canonical_question_uuid("item-1")
    assert payload.topic_id == topic_id
    assert payload.difficulty_bucket == DifficultyBucket.easy
    assert payload.stem_text == "What is attention?"
