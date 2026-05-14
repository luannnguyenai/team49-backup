import types
import unittest
import uuid
from unittest.mock import patch

from src.models.course import CourseAssetType
from src.services.learning_unit_service import _get_learning_unit_payload_from_db


class _FakeResult:
    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def first(self):
        return self._row

    def scalar_one_or_none(self):
        return self._scalar


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, _query):
        if not self._results:
            raise AssertionError("Unexpected extra query")
        return self._results.pop(0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSessionFactory:
    def __init__(self, results):
        self._results = results

    def __call__(self):
        return _FakeSession(self._results)


class LearningUnitServiceDbFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_db_payload_falls_back_to_course_asset_when_manifest_lookup_misses(self):
        unit_id = uuid.uuid4()
        unit = types.SimpleNamespace(
            id=unit_id,
            slug="lecture-01-seg1",
            title="Segment 1",
            unit_type=types.SimpleNamespace(value="lesson"),
            status=types.SimpleNamespace(value="ready"),
            entry_mode=types.SimpleNamespace(value="hybrid"),
            content_body="Body",
        )
        course = types.SimpleNamespace(slug="cs230", title="CS230")
        section = types.SimpleNamespace(title="Lecture 1")
        canonical_unit = types.SimpleNamespace(
            content_ref={"start_s": 0.0},
            lecture_order=1,
            transcript_path="courses/CS230/transcripts/lecture1.txt",
            lecture_id="cs230-lecture-1",
            lecture_title="Lecture 1",
        )
        asset = types.SimpleNamespace(
            asset_type=CourseAssetType.video,
            delivery_url="https://cdn.example.test/cs230/l1.mp4",
            storage_key="courses/CS230/videos/cs230-lecture-1.mp4",
            created_at=None,
        )

        fake_factory = _FakeSessionFactory(
            [
                _FakeResult(row=(unit, course, section, canonical_unit)),
                _FakeResult(scalar=asset),
            ]
        )

        with (
            patch("src.database.async_session_factory", new=fake_factory),
            patch(
                "src.services.learning_unit_service._find_course_video_filename",
                return_value=None,
            ),
            patch(
                "src.services.learning_unit_service._resolve_transcript_available",
                return_value=True,
            ),
            patch(
                "src.services.learning_unit_service._available_slide_lectures_for",
                return_value=set(),
            ),
        ):
            payload = await _get_learning_unit_payload_from_db("cs230", "lecture-01-seg1")

        assert payload is not None
        self.assertEqual(payload["content"]["video_url"], "https://cdn.example.test/cs230/l1.mp4")
        self.assertTrue(payload["tutor"]["enabled"])

    async def test_db_payload_falls_back_to_canonical_content_ref_url(self):
        unit = types.SimpleNamespace(
            id=uuid.uuid4(),
            slug="lecture-01-seg1",
            title="Segment 1",
            unit_type=types.SimpleNamespace(value="lesson"),
            status=types.SimpleNamespace(value="ready"),
            entry_mode=types.SimpleNamespace(value="hybrid"),
            content_body="Body",
        )
        course = types.SimpleNamespace(slug="cs230", title="CS230")
        section = types.SimpleNamespace(title="Lecture 1")
        canonical_unit = types.SimpleNamespace(
            content_ref={"start_s": 0.0, "video_url": "https://media.example.test/fallback.mp4"},
            lecture_order=1,
            transcript_path="courses/CS230/transcripts/lecture1.txt",
            lecture_id="cs230-lecture-1",
            lecture_title="Lecture 1",
        )

        fake_factory = _FakeSessionFactory(
            [
                _FakeResult(row=(unit, course, section, canonical_unit)),
                _FakeResult(scalar=None),
            ]
        )

        with (
            patch("src.database.async_session_factory", new=fake_factory),
            patch(
                "src.services.learning_unit_service._find_course_video_filename",
                return_value=None,
            ),
            patch(
                "src.services.learning_unit_service._resolve_transcript_available",
                return_value=True,
            ),
            patch(
                "src.services.learning_unit_service._available_slide_lectures_for",
                return_value=set(),
            ),
        ):
            payload = await _get_learning_unit_payload_from_db("cs230", "lecture-01-seg1")

        assert payload is not None
        self.assertEqual(payload["content"]["video_url"], "https://media.example.test/fallback.mp4")
        self.assertTrue(payload["tutor"]["enabled"])
