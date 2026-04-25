# tests/services/test_placement_assessment_service.py
from __future__ import annotations

import unittest
from unittest.mock import MagicMock


def _make_pair(item_id: str, difficulty: float | None):
    item = MagicMock()
    item.item_id = item_id
    return item, difficulty


class TestBucketSelect5(unittest.TestCase):
    def test_selects_1_easy_2_medium_2_hard(self):
        from src.services.placement_assessment_service import _bucket_select_5
        pairs = [
            _make_pair("e1", -1.0),
            _make_pair("e2", -0.6),
            _make_pair("m1", 0.0),
            _make_pair("m2", 0.3),
            _make_pair("m3", 0.5),
            _make_pair("h1", 0.8),
            _make_pair("h2", 1.2),
        ]
        selected = _bucket_select_5(pairs)
        self.assertEqual(len(selected), 5)
        item_ids = [p[0].item_id for p in selected]
        self.assertIn("e1", item_ids)   # 1 easy
        self.assertEqual(sum(1 for i in item_ids if i.startswith("m")), 2)  # 2 medium
        self.assertEqual(sum(1 for i in item_ids if i.startswith("h")), 2)  # 2 hard

    def test_fills_gaps_when_buckets_thin(self):
        from src.services.placement_assessment_service import _bucket_select_5
        # Only 3 items total — should return all 3, not error
        pairs = [
            _make_pair("a", -1.0),
            _make_pair("b", 0.0),
            _make_pair("c", 1.0),
        ]
        selected = _bucket_select_5(pairs)
        self.assertEqual(len(selected), 3)

    def test_none_difficulty_treated_as_medium(self):
        from src.services.placement_assessment_service import _bucket_select_5
        pairs = [
            _make_pair("n1", None),
            _make_pair("n2", None),
            _make_pair("h1", 0.8),
            _make_pair("h2", 1.0),
            _make_pair("e1", -0.8),
        ]
        selected = _bucket_select_5(pairs)
        self.assertEqual(len(selected), 5)

    def test_returns_at_most_5(self):
        from src.services.placement_assessment_service import _bucket_select_5
        pairs = [_make_pair(f"i{n}", float(n) * 0.2 - 1.0) for n in range(20)]
        selected = _bucket_select_5(pairs)
        self.assertLessEqual(len(selected), 5)


class TestClassifyDecision(unittest.TestCase):
    def test_skip_at_70(self):
        from src.services.placement_assessment_service import _classify_decision
        self.assertEqual(_classify_decision(70.0), "skip")
        self.assertEqual(_classify_decision(100.0), "skip")

    def test_review_between_50_and_70(self):
        from src.services.placement_assessment_service import _classify_decision
        self.assertEqual(_classify_decision(50.0), "review")
        self.assertEqual(_classify_decision(69.9), "review")

    def test_relearn_below_50(self):
        from src.services.placement_assessment_service import _classify_decision
        self.assertEqual(_classify_decision(49.9), "relearn")
        self.assertEqual(_classify_decision(0.0), "relearn")


if __name__ == "__main__":
    unittest.main()
