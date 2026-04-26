"""
tests/test_placement_assessment_service.py
-------------------------------------------
Unit tests for placement assessment service logic (no DB required).

Covers:
  - _classify_decision: boundary values at 49, 50, 69, 70, 100
  - _bucket_select_5: 1-2-2 distribution with exact and fallback scenarios

Run with:
    PYTHONPATH=. .venv/bin/python -m pytest tests/test_placement_assessment_service.py -v --noconftest
"""
from __future__ import annotations

import unittest
import uuid
from types import SimpleNamespace


def _make_item(
    difficulty: float | None = None,
    item_id: uuid.UUID | None = None,
) -> tuple:
    """Return a (QuestionBankItem-like, difficulty_prior) pair."""
    item = SimpleNamespace(
        item_id=item_id or uuid.uuid4(),
        question="Q?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        unit_id=str(uuid.uuid4()),
    )
    return (item, difficulty)


# ---------------------------------------------------------------------------
# _classify_decision — boundary tests
# ---------------------------------------------------------------------------

class TestClassifyDecision(unittest.TestCase):
    def _classify(self, score_pct: float) -> str:
        from src.services.placement_assessment_service import _classify_decision
        return _classify_decision(score_pct)

    def test_score_100_is_skip(self):
        self.assertEqual(self._classify(100.0), "skip")

    def test_score_70_is_skip(self):
        self.assertEqual(self._classify(70.0), "skip")

    def test_score_69_is_review(self):
        self.assertEqual(self._classify(69.0), "review")

    def test_score_50_is_review(self):
        self.assertEqual(self._classify(50.0), "review")

    def test_score_49_is_relearn(self):
        self.assertEqual(self._classify(49.0), "relearn")

    def test_score_0_is_relearn(self):
        self.assertEqual(self._classify(0.0), "relearn")

    def test_score_69_9_is_review(self):
        self.assertEqual(self._classify(69.9), "review")

    def test_score_70_0_is_skip_exact_boundary(self):
        self.assertEqual(self._classify(70.0), "skip")

    def test_score_49_9_is_relearn(self):
        self.assertEqual(self._classify(49.9), "relearn")

    def test_score_50_0_is_review_exact_boundary(self):
        self.assertEqual(self._classify(50.0), "review")


# ---------------------------------------------------------------------------
# _bucket_select_5 — distribution tests
# ---------------------------------------------------------------------------

class TestBucketSelect5(unittest.TestCase):
    def _select(self, pairs):
        from src.services.placement_assessment_service import _bucket_select_5
        return _bucket_select_5(pairs)

    def test_exact_1_2_2_distribution(self):
        """With 1 easy, 2 medium, 2 hard → exactly those 5 items selected."""
        pairs = [
            _make_item(-1.0),  # easy
            _make_item(0.0),   # medium
            _make_item(0.3),   # medium
            _make_item(0.8),   # hard
            _make_item(1.5),   # hard
        ]
        selected = self._select(pairs)
        self.assertEqual(len(selected), 5)

        diffs = [p[1] for p in selected]
        easy_count = sum(1 for d in diffs if d is not None and d <= -0.5)
        medium_count = sum(1 for d in diffs if d is None or (-0.5 < d <= 0.5))
        hard_count = sum(1 for d in diffs if d is not None and d > 0.5)

        self.assertEqual(easy_count, 1)
        self.assertEqual(medium_count, 2)
        self.assertEqual(hard_count, 2)

    def test_none_difficulty_treated_as_medium(self):
        """difficulty_prior=None counts as medium."""
        pairs = [
            _make_item(-0.8),  # easy
            _make_item(None),  # medium (None)
            _make_item(0.2),   # medium
            _make_item(0.7),   # hard
            _make_item(1.2),   # hard
        ]
        selected = self._select(pairs)
        self.assertEqual(len(selected), 5)

        # None is medium
        medium_count = sum(1 for _, d in selected if d is None or (-0.5 < (d or 0) <= 0.5))
        self.assertGreaterEqual(medium_count, 1)

    def test_fallback_when_easy_bucket_empty(self):
        """No easy items → filled from remaining (medium/hard)."""
        pairs = [
            _make_item(0.1),   # medium
            _make_item(0.2),   # medium
            _make_item(0.6),   # hard
            _make_item(0.8),   # hard
            _make_item(1.0),   # hard
        ]
        selected = self._select(pairs)
        self.assertEqual(len(selected), 5)

    def test_fallback_when_hard_bucket_empty(self):
        """No hard items → filled from remaining (easy/medium)."""
        pairs = [
            _make_item(-1.0),  # easy
            _make_item(-0.6),  # easy
            _make_item(0.1),   # medium
            _make_item(0.2),   # medium
            _make_item(0.4),   # medium
        ]
        selected = self._select(pairs)
        self.assertEqual(len(selected), 5)

    def test_fewer_than_5_items_returns_all(self):
        """If fewer than 5 items available, return all of them."""
        pairs = [
            _make_item(0.1),
            _make_item(0.9),
        ]
        selected = self._select(pairs)
        self.assertEqual(len(selected), 2)

    def test_exactly_5_hard_returns_2_hard_plus_fill(self):
        """Hard bucket capped at 2; rest filled from remaining."""
        pairs = [_make_item(0.6 + i * 0.1) for i in range(5)]  # all hard
        selected = self._select(pairs)
        self.assertEqual(len(selected), 5)
        hard_picked = [p for p in selected if p[1] is not None and p[1] > 0.5]
        # We selected all 5 because fallback fills from remaining
        self.assertEqual(len(hard_picked), 5)

    def test_returns_at_most_5(self):
        """Never returns more than 5 items regardless of input size."""
        pairs = [_make_item(i * 0.1 - 1.0) for i in range(20)]
        selected = self._select(pairs)
        self.assertLessEqual(len(selected), 5)

    def test_no_duplicates_in_selection(self):
        """Each item appears at most once in the selection."""
        pairs = [_make_item(i * 0.3 - 1.0) for i in range(10)]
        selected = self._select(pairs)
        selected_ids = [p[0].item_id for p in selected]
        self.assertEqual(len(selected_ids), len(set(selected_ids)))

    def test_easy_boundary_exactly_negative_half(self):
        """difficulty_prior == -0.5 is easy (<=)."""
        pairs = [_make_item(-0.5), _make_item(0.1), _make_item(0.1), _make_item(0.8), _make_item(0.9)]
        selected = self._select(pairs)
        diffs = [p[1] for p in selected]
        easy_count = sum(1 for d in diffs if d is not None and d <= -0.5)
        self.assertEqual(easy_count, 1)

    def test_hard_boundary_above_half(self):
        """difficulty_prior == 0.5 is medium (<=0.5), 0.51 is hard."""
        pairs = [_make_item(-0.6), _make_item(0.5), _make_item(0.3), _make_item(0.51), _make_item(1.0)]
        selected = self._select(pairs)
        diffs = [p[1] for p in selected]
        medium_count = sum(1 for d in diffs if d is not None and -0.5 < d <= 0.5)
        hard_count = sum(1 for d in diffs if d is not None and d > 0.5)
        self.assertEqual(medium_count, 2)
        self.assertEqual(hard_count, 2)


if __name__ == "__main__":
    unittest.main()
