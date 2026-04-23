import unittest
from pathlib import Path

from sqlalchemy import Float


class CanonicalContentModelTests(unittest.TestCase):
    def test_canonical_content_models_define_expected_tables(self):
        from src.models.canonical import (
            CanonicalUnit,
            ConceptKP,
            ItemCalibration,
            ItemKPMap,
            ItemPhaseMap,
            PrerequisiteEdge,
            PrunedEdge,
            QuestionBankItem,
            UnitKPMap,
        )

        self.assertEqual(ConceptKP.__tablename__, "concepts_kp")
        self.assertEqual(CanonicalUnit.__tablename__, "units")
        self.assertEqual(UnitKPMap.__tablename__, "unit_kp_map")
        self.assertEqual(QuestionBankItem.__tablename__, "question_bank")
        self.assertEqual(ItemCalibration.__tablename__, "item_calibration")
        self.assertEqual(ItemPhaseMap.__tablename__, "item_phase_map")
        self.assertEqual(ItemKPMap.__tablename__, "item_kp_map")
        self.assertEqual(PrerequisiteEdge.__tablename__, "prerequisite_edges")
        self.assertEqual(PrunedEdge.__tablename__, "pruned_edges")

    def test_canonical_content_models_preserve_natural_keys(self):
        from src.models.canonical import (
            CanonicalUnit,
            ConceptKP,
            ItemCalibration,
            PrerequisiteEdge,
            QuestionBankItem,
            UnitKPMap,
        )

        self.assertTrue(ConceptKP.__table__.c.kp_id.primary_key)
        self.assertTrue(CanonicalUnit.__table__.c.unit_id.primary_key)
        self.assertTrue(QuestionBankItem.__table__.c.item_id.primary_key)
        self.assertTrue(ItemCalibration.__table__.c.item_id.primary_key)
        self.assertTrue(UnitKPMap.__table__.c.unit_id.primary_key)
        self.assertTrue(UnitKPMap.__table__.c.kp_id.primary_key)
        self.assertTrue(PrerequisiteEdge.__table__.c.source_kp_id.primary_key)
        self.assertTrue(PrerequisiteEdge.__table__.c.target_kp_id.primary_key)

    def test_canonical_content_models_keep_audit_and_reserve_fields(self):
        from src.models.canonical import (
            CanonicalUnit,
            ConceptKP,
            ItemCalibration,
            PrerequisiteEdge,
            QuestionBankItem,
            UnitKPMap,
        )

        self.assertTrue(hasattr(ConceptKP, "description_embedding"))
        self.assertTrue(hasattr(ConceptKP, "source_file"))
        self.assertTrue(hasattr(CanonicalUnit, "topic_embedding"))
        self.assertTrue(hasattr(CanonicalUnit, "source_file"))
        self.assertTrue(hasattr(UnitKPMap, "coverage_weight"))
        self.assertTrue(hasattr(UnitKPMap, "source_local_kp_ids"))
        self.assertTrue(hasattr(QuestionBankItem, "source_ref"))
        self.assertTrue(hasattr(QuestionBankItem, "repair_history"))
        self.assertTrue(hasattr(ItemCalibration, "last_calibrated_at"))
        self.assertTrue(hasattr(PrerequisiteEdge, "edge_strength"))
        self.assertTrue(hasattr(PrerequisiteEdge, "bidirectional_score"))
        self.assertTrue(hasattr(PrerequisiteEdge, "p5_trace"))

    def test_canonical_content_models_store_numeric_difficulty_fields(self):
        from src.models.canonical import CanonicalUnit, ConceptKP

        self.assertIsInstance(ConceptKP.__table__.c.difficulty_level.type, Float)
        self.assertIsInstance(CanonicalUnit.__table__.c.difficulty.type, Float)

    def test_canonical_content_migration_mentions_all_tables(self):
        migration = Path(
            "alembic/versions/20260423_canonical_content_tables.py"
        ).read_text(encoding="utf-8")

        for table_name in (
            "concepts_kp",
            "units",
            "unit_kp_map",
            "question_bank",
            "item_calibration",
            "item_phase_map",
            "item_kp_map",
            "prerequisite_edges",
            "pruned_edges",
        ):
            self.assertIn(table_name, migration)


if __name__ == "__main__":
    unittest.main()
