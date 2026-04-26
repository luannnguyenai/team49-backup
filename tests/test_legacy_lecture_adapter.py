import unittest


class LegacyLectureAdapterTests(unittest.TestCase):
    def test_normalize_legacy_lecture_id_prefers_explicit_value(self):
        from src.services.legacy_lecture_adapter import normalize_legacy_lecture_id

        self.assertEqual(
            normalize_legacy_lecture_id("cs231n_lecture_01", order_index=1),
            "cs231n-lecture-1",
        )

    def test_normalize_legacy_lecture_id_falls_back_to_order_index(self):
        from src.services.legacy_lecture_adapter import normalize_legacy_lecture_id

        self.assertEqual(
            normalize_legacy_lecture_id(None, order_index=8),
            "cs231n-lecture-8",
        )

    def test_normalize_legacy_lecture_id_returns_none_when_unresolvable(self):
        from src.services.legacy_lecture_adapter import normalize_legacy_lecture_id

        self.assertIsNone(normalize_legacy_lecture_id(None, order_index=None))

    def test_get_unit_by_legacy_lecture_id_matches_normalized_bootstrap_value(self):
        from src.services.legacy_lecture_adapter import get_unit_by_legacy_lecture_id

        unit = get_unit_by_legacy_lecture_id("cs231n-lecture-1")

        self.assertIsNotNone(unit)
        self.assertEqual(unit["slug"], "lecture-1-introduction")

    def test_build_tutor_bridge_payload_marks_adapter_fields_explicitly(self):
        from src.services.legacy_lecture_adapter import build_tutor_bridge_payload

        payload = build_tutor_bridge_payload(
            tutor_enabled=True,
            unit_id="unit_lecture_01",
            legacy_lecture_id="cs231n-lecture-1",
        )

        self.assertEqual(payload["mode"], "in_context")
        self.assertEqual(payload["context_binding_id"], "ctx_unit_lecture_01")
        self.assertEqual(payload["legacy_lecture_id"], "cs231n-lecture-1")
