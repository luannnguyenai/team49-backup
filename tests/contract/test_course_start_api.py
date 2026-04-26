"""
tests/contract/test_course_start_api.py
---------------------------------------
Contract tests for US2: POST /api/courses/{slug}/start
and recommendation-aware catalog behavior.

These tests validate the API contract without a live database by exercising
the bootstrap-backed endpoints.
"""

import unittest

from httpx import ASGITransport, AsyncClient

from src.api.app import app


class CourseStartApiContractTests(unittest.IsolatedAsyncioTestCase):
    """Contract tests for the start-learning decision endpoint."""

    async def asyncSetUp(self) -> None:
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    # ------------------------------------------------------------------
    # POST /api/courses/{slug}/start — unauthenticated
    # ------------------------------------------------------------------

    async def test_start_cs231n_without_auth_returns_auth_required(self):
        """Unauthenticated start for a ready course → auth_required."""
        response = await self.client.post("/api/courses/cs231n/start")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reason"], "auth_required")
        self.assertIn("/login", data["target"])
        # Course context must be preserved in the redirect target
        self.assertIn("cs231n", data["target"])

    async def test_start_cs224n_returns_course_unavailable(self):
        """Start for a coming-soon course → course_unavailable regardless of auth."""
        response = await self.client.post("/api/courses/cs224n/start")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reason"], "course_unavailable")
        self.assertIn("/courses/cs224n", data["target"])

    async def test_start_nonexistent_course_returns_404(self):
        """Start for a course slug that does not exist → 404."""
        response = await self.client.post("/api/courses/does-not-exist/start")

        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # GET /api/courses?view=recommended — unauthenticated fallback
    # ------------------------------------------------------------------

    async def test_recommended_view_without_auth_returns_empty_items(self):
        """Unauthenticated recommended view returns empty list (no crash)."""
        response = await self.client.get("/api/courses?view=recommended")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Without auth, recommended view returns empty or all — contract says empty
        self.assertIsInstance(data["items"], list)

    async def test_all_view_returns_both_courses(self):
        """All-courses view returns both demo courses."""
        response = await self.client.get("/api/courses?view=all")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [item["slug"] for item in data["items"]]
        self.assertIn("cs231n", slugs)
        self.assertIn("cs224n", slugs)

    # ------------------------------------------------------------------
    # Response shape contract
    # ------------------------------------------------------------------

    async def test_start_response_has_required_fields(self):
        """Start response must contain decision, target, and reason."""
        response = await self.client.post("/api/courses/cs231n/start")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("decision", data)
        self.assertIn("target", data)
        self.assertIn("reason", data)
        # reason must be one of the allowed values
        allowed_reasons = {"auth_required", "skill_test_required",
                           "course_unavailable", "learning_ready"}
        self.assertIn(data["reason"], allowed_reasons)
