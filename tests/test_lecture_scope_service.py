import unittest

from src.services.lecture_scope_service import get_lecture_scope_metadata


class LectureScopeServiceTests(unittest.TestCase):
    def test_get_lecture_scope_metadata_resolves_cs231n_lecture(self):
        metadata = get_lecture_scope_metadata("cs231n-lecture-1")

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["lecture_number"], 1)
        self.assertIn("computer vision", metadata["scope_keywords"])

    def test_get_lecture_scope_metadata_returns_none_for_unknown_lecture(self):
        metadata = get_lecture_scope_metadata("unknown-lecture")

        self.assertIsNone(metadata)


if __name__ == "__main__":
    unittest.main()
