import unittest

from httpx import ASGITransport, AsyncClient

from src.api.app import app


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
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["items"][0]["slug"], "cs231n")
        self.assertEqual(data["items"][0]["status"], "ready")
        self.assertEqual(data["items"][1]["slug"], "cs224n")
        self.assertEqual(data["items"][1]["status"], "coming_soon")

    async def test_get_course_overview_returns_ready_entry_for_cs231n(self):
        response = await self.client.get("/api/courses/cs231n/overview")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course"]["slug"], "cs231n")
        self.assertEqual(data["entry"]["reason"], "learning_ready")
        self.assertEqual(data["entry"]["target"], "/courses/cs231n/start")

    async def test_get_course_overview_returns_blocked_entry_for_cs224n(self):
        response = await self.client.get("/api/courses/cs224n/overview")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["course"]["slug"], "cs224n")
        self.assertEqual(data["entry"]["reason"], "course_unavailable")
        self.assertEqual(data["entry"]["target"], "/courses/cs224n")
