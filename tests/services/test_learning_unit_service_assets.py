import unittest

from src.services.learning_unit_service import get_learning_unit_payload


class LearningUnitServiceAssetTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_lecture_reports_missing_slides_per_actual_files(self):
        payload = await get_learning_unit_payload("cs231n", "lecture-18-human-centered-ai")

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload.content.transcript_available)
        self.assertFalse(payload.content.slides_available)
