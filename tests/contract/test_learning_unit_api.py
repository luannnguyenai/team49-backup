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
        self.cs231n_payload = {
            "course": {
                "slug": "cs231n",
                "title": "CS231n: Deep Learning for Computer Vision",
            },
            "unit": {
                "id": "unit-lecture-1",
                "slug": "lecture-1-introduction",
                "title": "Lecture 1: Introduction",
                "lecture_title": "Lecture 1: Introduction",
                "lecture_order": 1,
                "unit_type": "lecture",
                "status": "ready",
                "entry_mode": "video",
            },
            "content": {
                "body_markdown": None,
                "video_url": "/data/courses/CS231n/videos/cs231n-2025-lecture01-introduction.mp4?exp=123&sig=abc",
                "transcript_available": True,
                "slides_available": True,
            },
            "tutor": {
                "enabled": True,
                "mode": "in_context",
                "context_binding_id": "ctx_unit-lecture-1",
                "legacy_lecture_id": "cs231n-lecture-1",
            },
        }
        self.cs230_payload = {
            "course": {
                "slug": "cs230",
                "title": "CS230: Deep Learning",
            },
            "unit": {
                "id": "unit-cs230-1",
                "slug": "lecture-01-seg1",
                "title": "Why deep learning won and where CS230 fits",
                "lecture_title": "Lecture 1: Introduction to Deep Learning",
                "lecture_order": 1,
                "unit_type": "lesson",
                "status": "ready",
                "entry_mode": "hybrid",
            },
            "content": {
                "body_markdown": "summary",
                "video_url": "/data/courses/CS230/videos/cs230-2025-lecture01-introduction-to-deep-learning.mp4?exp=123&sig=abc",
                "transcript_available": True,
                "slides_available": True,
            },
            "tutor": {
                "enabled": True,
                "mode": "in_context",
                "context_binding_id": "ctx_unit-cs230-1",
                "legacy_lecture_id": "cs230-2025-lecture01-introduction-to-deep-learning",
            },
        }

        self._access_patcher = patch(
            "src.routers.courses.assert_learning_access",
            new=AsyncMock(),
        )
        self._access_patcher.start()
        self._payload_patcher = patch(
            "src.routers.courses.get_learning_unit_payload",
            new=AsyncMock(side_effect=self._fake_learning_unit_payload),
        )
        self._payload_patcher.start()
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
        self._payload_patcher.stop()
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def _fake_learning_unit_payload(self, course_slug: str, unit_slug: str):
        if course_slug == "cs231n" and unit_slug in {
            "lecture-1-introduction",
            "lecture-2-linear-classifiers",
            "lecture-8-attention-transformers",
        }:
            payload = dict(self.cs231n_payload)
            payload["unit"] = dict(self.cs231n_payload["unit"])
            payload["unit"]["slug"] = unit_slug
            return payload
        if course_slug == "cs230" and unit_slug == "lecture-01-seg1":
            return self.cs230_payload
        return None

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
        self.assertTrue(parsed_video_url.path.startswith("/data/courses/CS231n/videos/"))
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

    async def test_cs230_unit_keeps_tutor_enabled_for_course_first_context(self):
        """Course-first units keep tutor enabled even without a legacy lecture row."""
        response = await self.client.get(
            "/api/courses/cs230/units/lecture-01-seg1"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["tutor"]["enabled"])
        self.assertEqual(data["tutor"]["mode"], "in_context")
        self.assertEqual(data["tutor"]["context_binding_id"], "ctx_unit-cs230-1")
        self.assertEqual(
            data["tutor"]["legacy_lecture_id"],
            "cs230-2025-lecture01-introduction-to-deep-learning",
        )

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
