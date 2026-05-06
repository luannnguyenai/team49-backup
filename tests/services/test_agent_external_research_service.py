import pytest

from src.services.agent_external_research_service import (
    AgentExternalResearchService,
    ExternalResearchDocument,
)
from src.services.agentic_rag_contracts import AgenticRAGFinal


class FixedExternalResearchService(AgentExternalResearchService):
    async def _act(self, queries):
        return [
            ExternalResearchDocument(
                title="CNN Explainer: Learning Convolutional Neural Networks with Interactive Visualization",
                url="https://arxiv.org/abs/2004.15004",
                snippet=(
                    "CNN Explainer helps learners understand convolutional neural networks, "
                    "including convolutions, filters, activation maps, and classification."
                ),
                source="paper",
            ),
            ExternalResearchDocument(
                title="Convolutional neural network",
                url="https://en.wikipedia.org/wiki/Convolutional_neural_network",
                snippet=(
                    "A convolutional neural network is a class of neural network commonly "
                    "applied to visual imagery using convolution operations."
                ),
                source="web",
            ),
        ]


class RecordingResponder:
    def __init__(self, answers: list[str] | None = None):
        self.calls = []
        self.answers = answers or [
            (
                "CNN là mạng neural dùng phép tích chập để học đặc trưng cục bộ, "
                "thường dùng cho ảnh và các dữ liệu có cấu trúc không gian. [1]"
            )
        ]

    def rag_respond(self, **kwargs):
        self.calls.append(kwargs)
        answer = self.answers[min(len(self.calls) - 1, len(self.answers) - 1)]
        return AgenticRAGFinal(
            answer_markdown=answer,
            evidence_status="grounded",
            evidence_sufficient=True,
        )


@pytest.mark.asyncio
async def test_external_research_synthesizes_answer_from_observed_sources():
    responder = RecordingResponder()
    service = FixedExternalResearchService(responder=responder)

    result = await service.answer(message="Giải thích CNN", recent_messages=[])

    assert "I searched web and paper sources" not in result.answer_markdown
    assert "Most relevant evidence" not in result.answer_markdown
    assert result.answer_markdown.startswith("CNN là mạng neural")
    assert (
        "[1]"
        "(https://arxiv.org/abs/2004.15004)" in result.answer_markdown
    )
    assert "## Sources" in result.answer_markdown
    assert (
        "1. [CNN Explainer: Learning Convolutional Neural Networks with Interactive Visualization]"
        "(https://arxiv.org/abs/2004.15004)" in result.answer_markdown
    )
    assert "— Paper" in result.answer_markdown
    assert "[^" not in result.answer_markdown
    assert result.citations[0].source == "paper"
    assert responder.calls
    observation = responder.calls[0]["observations"][0]
    assert observation["tool"] == "search_web_papers"
    assert "CNN Explainer" in str(observation)


@pytest.mark.asyncio
async def test_external_research_retries_truncated_outline_synthesis():
    responder = RecordingResponder(
        answers=[
            "1) RCNN giải quyết bài toán gì?\n\nRCNN dự đoán class và bounding box.",
            (
                "RCNN là họ mô hình phát hiện đối tượng dựa trên region proposals. "
                "Thay vì quét mọi cửa sổ ảnh, mô hình chọn các vùng ứng viên rồi phân loại "
                "và tinh chỉnh bounding box cho từng vùng.\n\n"
                "Ý chính là tách bài toán detection thành hai phần: tìm vùng có khả năng chứa "
                "đối tượng, sau đó dự đoán nhãn và tọa độ hộp bao. Cách này làm pipeline dễ "
                "hiểu hơn, dù các biến thể đầu tiên khá tốn chi phí tính toán."
            ),
        ]
    )
    service = FixedExternalResearchService(responder=responder)

    result = await service.answer(message="Giải thích thêm về RCNN", recent_messages=[])

    assert len(responder.calls) == 2
    assert "RCNN là họ mô hình" in result.answer_markdown
    assert "1) RCNN giải quyết bài toán gì?" not in result.answer_markdown
    assert responder.calls[1]["thought"]["quality_retry"] == "complete_external_answer"
