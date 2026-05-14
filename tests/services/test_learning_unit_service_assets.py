import unittest
from pathlib import Path

from src.services.learning_unit_service import get_learning_unit_payload


@unittest.skipUnless(
    Path("data/bootstrap/units.json").exists(),
    "bootstrap units fixture is not present in this environment",
)
class LearningUnitServiceAssetTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_lecture_reports_missing_slides_per_actual_files(self):
        payload = await get_learning_unit_payload("cs231n", "lecture-18-human-centered-ai")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload.content.transcript_available)
        self.assertFalse(payload.content.slides_available)
