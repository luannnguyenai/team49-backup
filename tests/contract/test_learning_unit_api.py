"""
tests/contract/test_learning_unit_api.py
----------------------------------------
Contract tests for US3: GET /api/courses/{course_slug}/units/{unit_slug}
and legacy tutor compatibility behavior.
"""

import unittest
import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.dependencies.auth import get_current_onboarded_user


class LearningUnitApiContractTests(unittest.IsolatedAsyncioTestCase):
    """Contract tests for the learning unit endpoint."""

    async def asyncSetUp(self) -> None:
        self._access_patcher = patch(
            "src.routers.courses.assert_learning_access",
            new=AsyncMock(),
        )
        self._access_patcher.start()
        app.dependency_overrides[get_current_onboarded_user] = lambda: SimpleNamespace(
            id=uuid.uuid4(),
            is_onboarded=True,
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        self._access_patcher.stop()
        app.dependency_overrides.clear()
        await self.client.aclose()

    # ------------------------------------------------------------------
    # GET /api/courses/{slug}/units/{unit_slug}
    # ------------------------------------------------------------------

    async def test_get_first_lecture_unit_returns_valid_payload(self):
        """First CS231n lecture unit returns complete LearningUnitResponse."""
        response = await self.client.get(
            "/api/courses/cs231n/units/lecture-1-introduction"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Course summary
        self.assertEqual(data["course"]["slug"], "cs231n")
        self.assertIn("CS231n", data["course"]["title"])

        # Unit summary
        self.assertEqual(data["unit"]["slug"], "lecture-1-introduction")
        self.assertEqual(data["unit"]["unit_type"], "lecture")
        self.assertEqual(data["unit"]["status"], "ready")
        self.assertEqual(data["unit"]["entry_mode"], "video")

        # Content payload
        self.assertIn("content", data)
        self.assertIn("video_url", data["content"])
        self.assertIsNotNone(data["content"]["video_url"])
        parsed_video_url = urlparse(data["content"]["video_url"])
        self.assertTrue(parsed_video_url.path.startswith("/data/CS231n/videos/"))
        self.assertIn("exp", parse_qs(parsed_video_url.query))
        self.assertIn("sig", parse_qs(parsed_video_url.query))

        # Tutor context
        self.assertIn("tutor", data)
        self.assertIsInstance(data["tutor"]["enabled"], bool)
        self.assertIn("mode", data["tutor"])
        self.assertEqual(data["tutor"]["legacy_lecture_id"], "cs231n-lecture-1")

    async def test_get_unit_for_nonexistent_course_returns_404(self):
        """Unit lookup for non-existent course → 404."""
        response = await self.client.get(
            "/api/courses/does-not-exist/units/lecture-1"
        )
        self.assertEqual(response.status_code, 404)

    async def test_get_nonexistent_unit_returns_404(self):
        """Unit lookup for non-existent unit slug → 404."""
        response = await self.client.get(
            "/api/courses/cs231n/units/does-not-exist"
        )
        self.assertEqual(response.status_code, 404)

    async def test_tutor_context_has_binding_id_for_ready_unit(self):
        """Ready unit with video should have tutor.context_binding_id set."""
        response = await self.client.get(
            "/api/courses/cs231n/units/lecture-1-introduction"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Tutor should be enabled for ready lecture units
        if data["content"]["video_url"] is not None:
            self.assertTrue(data["tutor"]["enabled"])
            self.assertEqual(data["tutor"]["mode"], "in_context")
            self.assertIsNotNone(data["tutor"]["context_binding_id"])

    async def test_response_shape_matches_contract(self):
        """Response must contain all required top-level keys."""
        response = await self.client.get(
            "/api/courses/cs231n/units/lecture-1-introduction"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Top-level keys per contract
        self.assertIn("course", data)
        self.assertIn("unit", data)
        self.assertIn("content", data)
        self.assertIn("tutor", data)

        # Course keys
        self.assertIn("slug", data["course"])
        self.assertIn("title", data["course"])

        # Unit keys
        for key in ["id", "slug", "title", "unit_type", "status", "entry_mode"]:
            self.assertIn(key, data["unit"])

        # Content keys
        for key in ["body_markdown", "video_url", "transcript_available", "slides_available"]:
            self.assertIn(key, data["content"])

        # Tutor keys
        for key in ["enabled", "mode", "context_binding_id", "legacy_lecture_id"]:
            self.assertIn(key, data["tutor"])

    async def test_multiple_units_accessible(self):
        """Multiple CS231n lecture units should be accessible."""
        slugs = [
            "lecture-1-introduction",
            "lecture-2-linear-classifiers",
            "lecture-8-attention-transformers",
        ]
        for slug in slugs:
            response = await self.client.get(f"/api/courses/cs231n/units/{slug}")
            self.assertEqual(
                response.status_code,
                200,
                f"Unit '{slug}' should be accessible but got {response.status_code}",
            )
