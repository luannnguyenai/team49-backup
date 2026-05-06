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
    def __init__(self):
        self.calls = []

    def rag_respond(self, **kwargs):
        self.calls.append(kwargs)
        return AgenticRAGFinal(
            answer_markdown=(
                "CNN là mạng neural dùng phép tích chập để học đặc trưng cục bộ, "
                "thường dùng cho ảnh và các dữ liệu có cấu trúc không gian."
            ),
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
    assert result.citations[0].source == "paper"
    assert responder.calls
    observation = responder.calls[0]["observations"][0]
    assert observation["tool"] == "search_web_papers"
    assert "CNN Explainer" in str(observation)
