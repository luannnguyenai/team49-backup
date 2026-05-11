import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.api.app import AskRequest, RateRequest, ask_question, rate_answer
from src.services.model_registry import ChatModelUnavailableError


class _FakeDb:
    def __init__(self, *results):
        self._results = list(results)
        self.commit = AsyncMock()

    async def execute(self, *_args, **_kwargs):
        value = self._results.pop(0) if self._results else None
        return SimpleNamespace(scalar_one_or_none=lambda: value)


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

    async def test_ask_question_allows_canonical_context_binding_without_legacy_lecture(self):
        canonical_unit_id = uuid.uuid4()

        with patch(
            "src.api.app.get_context_and_stream_langgraph",
            return_value=iter(['{"a":"ok"}\n']),
        ) as mock_stream:
            response = await ask_question(
                AskRequest(
                    lecture_id="missing-lecture",
                    current_timestamp=12,
                    question="Explain this part",
                    context_binding_id=f"ctx_{canonical_unit_id}",
                ),
                db=_FakeDb(None, canonical_unit_id),
            )

        self.assertEqual(response.status_code, 200)
        mock_stream.assert_called_once_with(
            "missing-lecture",
            12,
            "Explain this part",
            image_base64=None,
            context_binding_id=f"ctx_{canonical_unit_id}",
            user_id=None,
            chat_model_id="default",
        )

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
            user_id=None,
            chat_model_id="default",
        )
        self.assertEqual(response.headers["content-type"], "application/x-ndjson")
        self.assertEqual(response.headers["cache-control"], "no-cache, no-transform")
        self.assertEqual(response.headers["x-accel-buffering"], "no")

    async def test_ask_question_forwards_chat_model_id_to_tutor_service(self):
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
                patch("src.api.app.ensure_chat_model_available", new=AsyncMock()),
            ):
                response = await client.post(
                    "/api/lectures/ask",
                    json={
                        "lecture_id": "cs231n-lecture-1",
                        "current_timestamp": 12,
                        "question": "Explain this part",
                        "chatModelId": "qwen35_4b",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_stream.call_args.kwargs["chat_model_id"], "qwen35_4b")

    async def test_ask_question_rejects_unavailable_chat_model(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            with (
                patch("src.api.app._ensure_lecture_exists", new=AsyncMock()),
                patch(
                    "src.api.app.ensure_chat_model_available",
                    new=AsyncMock(
                        side_effect=ChatModelUnavailableError(
                            model_id="qwen35_4b",
                            label="Qwen 3.5 4B",
                            status="down",
                        )
                    ),
                ),
                patch("src.api.app.get_context_and_stream_langgraph") as mock_stream,
            ):
                response = await client.post(
                    "/api/lectures/ask",
                    json={
                        "lecture_id": "cs231n-lecture-1",
                        "current_timestamp": 12,
                        "question": "Explain this part",
                        "chatModelId": "qwen35_4b",
                    },
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "chat_model_unavailable")
        self.assertEqual(response.json()["detail"]["modelId"], "qwen35_4b")
        mock_stream.assert_not_called()

    async def test_ask_question_forwards_authenticated_user_id_to_tutor_service(self):
        fake_user = SimpleNamespace(id=uuid.uuid4())

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            with (
                patch("src.api.app._ensure_lecture_exists", new=AsyncMock()),
                patch(
                    "src.api.app.get_current_user_from_request",
                    new=AsyncMock(return_value=fake_user),
                ),
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
                    },
                    headers={"Authorization": "Bearer fake-token"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_stream.call_args.kwargs["user_id"], str(fake_user.id))

    async def test_rate_answer_commits_and_scores_trace_when_trace_id_exists(self):
        qa_row = SimpleNamespace(rating=None, langfuse_trace_id="trace-123")
        fake_db = _FakeDb(qa_row)

        with patch("src.api.app.score_trace", return_value=True) as mock_score:
            result = await rate_answer(qa_id=7, req=RateRequest(rating=1), db=fake_db)

        self.assertEqual(qa_row.rating, 1)
        fake_db.commit.assert_awaited_once()
        mock_score.assert_called_once_with(
            trace_id="trace-123",
            name="user_thumb",
            value=1.0,
            comment="qa_id=7",
        )
        self.assertEqual(result["status"], "ok")

    async def test_rate_answer_commits_without_scoring_when_trace_id_missing(self):
        qa_row = SimpleNamespace(rating=None, langfuse_trace_id=None)
        fake_db = _FakeDb(qa_row)

        with patch("src.api.app.score_trace", return_value=False) as mock_score:
            await rate_answer(qa_id=8, req=RateRequest(rating=-1), db=fake_db)

        self.assertEqual(qa_row.rating, -1)
        fake_db.commit.assert_awaited_once()
        mock_score.assert_not_called()


if __name__ == "__main__":
    unittest.main()
