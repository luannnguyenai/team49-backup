import unittest
import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.schemas.course import CourseCatalogItem, CourseCatalogResponse


class CourseCatalogApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_get_courses_returns_both_demo_courses(self):
        response = await self.client.get("/api/courses")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["items"]), 2)
        items_by_slug = {item["slug"]: item for item in data["items"]}
        self.assertEqual(items_by_slug["cs231n"]["status"], "ready")
        self.assertIn("progress_percent", items_by_slug["cs231n"])
        self.assertIsNone(items_by_slug["cs231n"]["progress_percent"])
        self.assertEqual(items_by_slug["cs224n"]["status"], "ready")
        self.assertIn("progress_percent", items_by_slug["cs224n"])
        self.assertIsNone(items_by_slug["cs224n"]["progress_percent"])

    async def test_get_courses_can_return_progress_percent(self):
        response_payload = CourseCatalogResponse(
            items=[
                CourseCatalogItem(
                    id=str(uuid.uuid4()),
                    slug="db-course",
                    title="DB Course",
                    short_description="From database",
                    status="ready",
                    cover_image_url=None,
                    hero_badge="Ready",
                    is_recommended=False,
                    progress_percent=40,
                )
            ]
        )

        with patch(
            "src.routers.courses.list_course_catalog",
            new=AsyncMock(return_value=response_payload),
        ):
            response = await self.client.get("/api/courses")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["items"][0]["progress_percent"], 40)

    async def test_get_course_units_includes_is_completed_field(self):
        with patch(
            "src.routers.courses.list_course_units_db_first",
            new=AsyncMock(
                return_value=[
                    {
                        "slug": "db-unit-1",
                        "title": "Lecture 1",
                        "status": "ready",
                        "unit_type": "lecture",
                        "order_index": 1,
                        "lecture_label": "Lecture 01",
                        "canonical_unit_id": "local::db-course::seg1",
                        "is_completed": True,
                    }
                ]
            ),
        ):
            response = await self.client.get("/api/courses/db-course/units")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["units"][0]["is_completed"])
        self.assertEqual(data["units"][0]["canonical_unit_id"], "local::db-course::seg1")

    async def test_get_course_overview_returns_ready_entry_for_cs231n(self):
        response = await self.client.get("/api/courses/cs231n/overview")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course"]["slug"], "cs231n")
        self.assertEqual(data["entry"]["reason"], "learning_ready")
        self.assertEqual(data["entry"]["target"], "/courses/cs231n/start")

    async def test_get_course_overview_returns_ready_entry_for_cs224n(self):
        response = await self.client.get("/api/courses/cs224n/overview")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course"]["slug"], "cs224n")
        self.assertEqual(data["entry"]["reason"], "learning_ready")
        self.assertEqual(data["entry"]["target"], "/courses/cs224n/start")
