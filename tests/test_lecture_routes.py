import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.api.app import AskRequest, ask_question


class _FakeDb:
    async def execute(self, *_args, **_kwargs):
        return SimpleNamespace(scalar_one_or_none=lambda: None)


class LectureRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_ask_question_preserves_404_when_lecture_is_missing(self):
        with self.assertRaises(HTTPException) as ctx:
            await ask_question(
                AskRequest(
                    lecture_id="missing-lecture",
                    current_timestamp=0,
                    question="What is this lecture about?",
                ),
                db=_FakeDb(),
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Lecture not found")

    async def test_ask_question_forwards_context_binding_id_to_tutor_service(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            with (
                patch("src.api.app._ensure_lecture_exists", new=AsyncMock()),
                patch(
                    "src.api.app.get_context_and_stream_langgraph",
                    return_value=iter(['{"a":"ok"}\n']),
                ) as mock_stream,
            ):
                response = await client.post(
                    "/api/lectures/ask",
                    json={
                        "lecture_id": "cs231n-lecture-1",
                        "current_timestamp": 12,
                        "question": "Explain this part",
                        "context_binding_id": "ctx_unit_lecture_01",
                    },
                )

        self.assertEqual(response.status_code, 200)
        mock_stream.assert_called_once_with(
            "cs231n-lecture-1",
            12.0,
            "Explain this part",
            image_base64=None,
            context_binding_id="ctx_unit_lecture_01",
        )


if __name__ == "__main__":
    unittest.main()
