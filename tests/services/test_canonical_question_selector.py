from dataclasses import dataclass

import pytest

from src.services.canonical_question_selector import CanonicalQuestionSelector


@dataclass
class FakeItem:
    item_id: str
    difficulty: str
    question_intent: str


class FakeRepo:
    async def get_items_for_phase(self, *, phase, canonical_unit_ids, kp_ids=None, limit=50):
        return [
            FakeItem("q-hard", "hard", "application"),
            FakeItem("q-easy", "easy", "conceptual"),
            FakeItem("q-medium", "medium", "diagnostic"),
        ]


@pytest.mark.asyncio
async def test_selector_balances_difficulty_for_phase():
    selector = CanonicalQuestionSelector(FakeRepo())

    selected = await selector.select_for_phase(
        phase="mini_quiz",
        canonical_unit_ids=["unit-a"],
        count=2,
    )

    assert [item.item_id for item in selected] == ["q-medium", "q-easy"]
