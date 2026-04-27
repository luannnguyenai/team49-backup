import types
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from src.services.course_catalog_service import get_course_overview, list_course_catalog
from src.services.course_entry_service import get_start_learning_decision
from src.services.learning_unit_service import get_learning_unit_payload, list_course_units_db_first


class CourseDbReadPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_course_catalog_prefers_db_rows_when_available(self):
        db_rows = [
            {
                "id": str(uuid.uuid4()),
                "slug": "db-course",
                "title": "DB Course",
                "short_description": "From database",
                "status": "ready",
                "cover_image_url": None,
                "hero_badge": "Ready",
                "is_recommended": False,
            }
        ]

        with patch(
            "src.services.course_catalog_service._list_catalog_from_db",
            new=AsyncMock(return_value=db_rows),
            create=True,
        ):
            result = await list_course_catalog()

        self.assertEqual([item.slug for item in result.items], ["db-course"])

    async def test_list_course_catalog_includes_progress_percent_for_authenticated_user(self):
        user = types.SimpleNamespace(id=uuid.uuid4())
        db_rows = [
            {
                "id": str(uuid.uuid4()),
                "slug": "db-course",
                "title": "DB Course",
                "short_description": "From database",
                "status": "ready",
                "cover_image_url": None,
                "hero_badge": "Ready",
                "is_recommended": False,
            }
        ]

        with (
            patch(
                "src.services.course_catalog_service._list_catalog_from_db",
                new=AsyncMock(return_value=db_rows),
                create=True,
            ),
            patch(
                "src.services.course_catalog_service._get_recommended_course_slugs",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "src.services.course_catalog_service._get_course_progress_percents",
                new=AsyncMock(return_value={db_rows[0]["id"]: 50}),
                create=True,
            ),
        ):
            result = await list_course_catalog(user=user)

        self.assertEqual(result.items[0].progress_percent, 50)

    async def test_list_course_catalog_keeps_progress_percent_none_for_anonymous_user(self):
        db_rows = [
            {
                "id": str(uuid.uuid4()),
                "slug": "db-course",
                "title": "DB Course",
                "short_description": "From database",
                "status": "ready",
                "cover_image_url": None,
                "hero_badge": "Ready",
                "is_recommended": False,
            }
        ]
        progress_mock = AsyncMock(return_value={db_rows[0]["id"]: 50})

        with (
            patch(
                "src.services.course_catalog_service._list_catalog_from_db",
                new=AsyncMock(return_value=db_rows),
                create=True,
            ),
            patch(
                "src.services.course_catalog_service._get_course_progress_percents",
                new=progress_mock,
                create=True,
            ),
        ):
            result = await list_course_catalog()

        self.assertIsNone(result.items[0].progress_percent)
        progress_mock.assert_not_awaited()

    async def test_get_course_overview_prefers_db_rows_when_available(self):
        db_row = {
            "course": {
                "id": str(uuid.uuid4()),
                "slug": "db-course",
                "title": "DB Course",
                "short_description": "From database",
                "status": "ready",
                "cover_image_url": None,
                "hero_badge": "Ready",
                "is_recommended": False,
            },
            "overview": {
                "headline": "Database first",
                "subheadline": None,
                "summary_markdown": "Overview body",
                "learning_outcomes": ["Outcome"],
                "target_audience": None,
                "prerequisites_summary": None,
                "estimated_duration_text": "3 units",
                "structure_snapshot": {"summary": "Structured"},
                "cta_label": "Start",
            },
        }

        with patch(
            "src.services.course_catalog_service._get_course_overview_from_db",
            new=AsyncMock(return_value=db_row),
            create=True,
        ):
            result = await get_course_overview("db-course")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.course.slug, "db-course")
        self.assertEqual(result.overview.headline, "Database first")

    async def test_start_learning_decision_prefers_db_course_and_first_unit(self):
        user = types.SimpleNamespace(
            id=uuid.uuid4(),
            is_onboarded=True,
        )

        with (
            patch(
                "src.services.course_entry_service._get_course_gate_snapshot_from_db",
                new=AsyncMock(return_value={"slug": "db-course", "status": "ready"}),
                create=True,
            ),
            patch(
                "src.services.course_entry_service._get_first_unit_slug_from_db",
                new=AsyncMock(return_value="db-unit"),
                create=True,
            ),
            patch(
                "src.services.course_entry_service._check_skill_test_completed",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await get_start_learning_decision("db-course", user=user)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.reason, "learning_ready")
        self.assertEqual(result.target, "/courses/db-course/learn/db-unit")

    async def test_get_learning_unit_payload_prefers_db_rows_when_available(self):
        db_row = {
            "course": {"slug": "db-course", "title": "DB Course"},
            "unit": {
                "id": str(uuid.uuid4()),
                "slug": "db-unit",
                "title": "DB Unit",
                "unit_type": "lecture",
                "status": "ready",
                "entry_mode": "video",
            },
            "content": {
                "body_markdown": "Body",
                "video_url": "/data/courses/db/videos/lecture1.mp4?exp=1&sig=x",
                "transcript_available": True,
                "slides_available": False,
            },
            "tutor": {
                "enabled": False,
                "mode": "disabled",
                "context_binding_id": None,
                "legacy_lecture_id": None,
            },
        }

        with patch(
            "src.services.learning_unit_service._get_learning_unit_payload_from_db",
            new=AsyncMock(return_value=db_row),
            create=True,
        ):
            result = await get_learning_unit_payload("db-course", "db-unit")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.course.slug, "db-course")
        self.assertEqual(result.unit.slug, "db-unit")
        self.assertEqual(result.content.body_markdown, "Body")

    async def test_list_course_units_db_first_marks_completed_units_for_authenticated_user(self):
        user_id = uuid.uuid4()
        completed_unit_id = uuid.uuid4()
        pending_unit_id = uuid.uuid4()
        db_units = [
            {
                "id": str(completed_unit_id),
                "slug": "db-unit-1",
                "title": "Lecture 1",
                "status": "ready",
                "unit_type": "lecture",
                "order_index": 1,
                "lecture_label": "Lecture 01",
            },
            {
                "id": str(pending_unit_id),
                "slug": "db-unit-2",
                "title": "Lecture 2",
                "status": "ready",
                "unit_type": "lecture",
                "order_index": 2,
                "lecture_label": "Lecture 02",
            },
        ]

        with (
            patch(
                "src.services.learning_unit_service._list_course_units_from_db",
                new=AsyncMock(return_value=db_units),
                create=True,
            ),
            patch(
                "src.services.learning_unit_service._get_completed_learning_unit_ids",
                new=AsyncMock(return_value={completed_unit_id}),
                create=True,
            ),
        ):
            result = await list_course_units_db_first("db-course", user_id=user_id)

        self.assertTrue(result[0]["is_completed"])
        self.assertFalse(result[1]["is_completed"])

    async def test_list_course_units_db_first_defaults_completion_to_false_without_user(self):
        db_units = [
            {
                "id": str(uuid.uuid4()),
                "slug": "db-unit-1",
                "title": "Lecture 1",
                "status": "ready",
                "unit_type": "lecture",
                "order_index": 1,
                "lecture_label": "Lecture 01",
            }
        ]

        with patch(
            "src.services.learning_unit_service._list_course_units_from_db",
            new=AsyncMock(return_value=db_units),
            create=True,
        ):
            result = await list_course_units_db_first("db-course")

        self.assertFalse(result[0]["is_completed"])
