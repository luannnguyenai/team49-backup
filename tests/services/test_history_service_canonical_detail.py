from types import SimpleNamespace

from src.models.learning import SelectedAnswer
from src.services.history_service import _answer_index_to_letter, _interaction_detail_from_row


def test_answer_index_to_letter_handles_canonical_indices():
    assert _answer_index_to_letter(0) == "A"
    assert _answer_index_to_letter(3) == "D"
    assert _answer_index_to_letter(None) == ""
    assert _answer_index_to_letter(9) == ""


def test_interaction_detail_from_row_renders_canonical_question_bank_item():
    inter = SimpleNamespace(
        canonical_item_id="item-1",
        sequence_position=2,
        selected_answer=SelectedAnswer.B,
        is_correct=True,
        response_time_ms=1234,
    )
    canonical_item = SimpleNamespace(
        item_id="item-1",
        unit_id="cs231n::lecture01::unit01",
        question="What is a convolution?",
        choices=["A", "B", "C", "D"],
        answer_index=1,
        question_intent="conceptual",
        difficulty="medium",
        explanation="Because B is correct.",
    )

    detail = _interaction_detail_from_row(inter, None, canonical_item, None)

    assert detail.question_id is None
    assert detail.canonical_item_id == "item-1"
    assert detail.learning_unit_title == "cs231n::lecture01::unit01"
    assert detail.stem_text == "What is a convolution?"
    assert detail.bloom_level == "conceptual"
    assert detail.difficulty_bucket == "medium"
    assert detail.selected_answer == "B"
    assert detail.correct_answer == "B"
    assert detail.explanation_text == "Because B is correct."
