import unittest

from fastapi import HTTPException

from src.api.app import AskRequest, ask_question


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _FakeDb:
    def query(self, *_args, **_kwargs):
        return _FakeQuery()


class LectureRouteTests(unittest.TestCase):
    def test_ask_question_preserves_404_when_lecture_is_missing(self):
        with self.assertRaises(HTTPException) as ctx:
            ask_question(
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
