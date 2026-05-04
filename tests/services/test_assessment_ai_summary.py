import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.services.assessment_service import _parse_assessment_ai_summary


def test_parse_assessment_ai_summary_accepts_json_payload():
    response = _parse_assessment_ai_summary(
        """
        {
          "summary": "Bạn đang vững phần CNN cơ bản, nhưng còn hổng ở activation.",
          "highlights": ["Bỏ qua phần đã đạt 100%", "Ôn lại phần sai 0/1"],
          "next_step": "Bắt đầu bằng phần activation trước."
        }
        """
    )

    assert response.available is True
    assert response.summary == "Bạn đang vững phần CNN cơ bản, nhưng còn hổng ở activation."
    assert response.highlights == ["Bỏ qua phần đã đạt 100%", "Ôn lại phần sai 0/1"]
    assert response.next_step == "Bắt đầu bằng phần activation trước."


def test_parse_assessment_ai_summary_returns_unavailable_without_summary():
    response = _parse_assessment_ai_summary('{"highlights": ["ok"]}')

    assert response.available is False
    assert response.summary is None


class AssessmentAISummaryTracingTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_assessment_ai_summary_passes_langfuse_callbacks_and_metadata(self):
        from src.services.assessment_service import generate_assessment_ai_summary

        session_id = uuid.uuid4()
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = SimpleNamespace(
            content='{"summary":"ok","highlights":[],"next_step":"next"}'
        )
        fake_result = SimpleNamespace(
            overall_score_percent=75.0,
            topic_decisions=[],
            learning_unit_results=[],
        )

        with (
            patch("src.services.assessment_service.get_assessment_results", return_value=fake_result),
            patch("src.services.llm_rate_limiter.enforce_llm_rate_limit"),
            patch("langchain.chat_models.init_chat_model", return_value=fake_llm),
            patch("src.services.assessment_service.llm_callbacks", return_value=["cb"]),
            patch("src.services.assessment_service.start_langfuse_root_span", return_value=MagicMock(__enter__=lambda s: None, __exit__=lambda s, exc_type, exc, tb: False)),
            patch("src.services.assessment_service.propagate_langfuse_attributes", return_value=MagicMock(__enter__=lambda s: None, __exit__=lambda s, exc_type, exc, tb: False)),
        ):
            response = await generate_assessment_ai_summary(
                db=MagicMock(),
                user_id=uuid.uuid4(),
                session_id=session_id,
            )

        assert response.available is True
        _, kwargs = fake_llm.invoke.call_args
        assert kwargs["config"]["callbacks"] == ["cb"]
        assert kwargs["config"]["metadata"]["langfuse_session_id"] == str(session_id)
        assert kwargs["config"]["metadata"]["langfuse_tags"] == ["assessment", "summary"]
