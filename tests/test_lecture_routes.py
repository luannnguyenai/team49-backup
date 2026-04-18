import unittest
from types import SimpleNamespace

from fastapi import HTTPException

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


if __name__ == "__main__":
    unittest.main()
