import pytest

from src.schemas.agent import AgentCitation
from src.services.agent_external_research_service import (
    AgentExternalResearchService,
    ExternalResearchDocument,
    SearchPlan,
)
from src.services.agent_external_citation_manager import ExternalCitationManager
from src.services.agentic_rag_contracts import AgenticRAGFinal


class FixedExternalResearchService(AgentExternalResearchService):
    async def _act(self, plan):
        if any("rcnn" in query.casefold() for query in plan.queries):
            return [
                ExternalResearchDocument(
                    title="Rich feature hierarchies for accurate object detection and semantic segmentation",
                    url="https://arxiv.org/abs/1311.2524",
                    snippet=(
                        "R-CNN applies region proposals and convolutional neural network features "
                        "for object detection and semantic segmentation."
                    ),
                    source="paper",
                )
            ]
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
    assert "- Paper" in result.answer_markdown
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


def test_external_research_plans_clean_cnn_queries_for_vietnamese_request():
    service = AgentExternalResearchService()

    plan = service._plan_search("tìm thông tin về CNN")

    assert plan == SearchPlan(tools=("web",), queries=("CNN",))


def test_external_research_selects_paper_tool_only_for_paper_intent():
    service = AgentExternalResearchService()

    plan = service._plan_search("find arxiv papers about CNN pruning")

    assert plan == SearchPlan(tools=("paper",), queries=("CNN pruning",))


def test_external_research_selects_both_tools_when_user_asks_for_web_and_papers():
    service = AgentExternalResearchService()

    plan = service._plan_search("search web and papers about CNN pruning")

    assert plan == SearchPlan(tools=("web", "paper"), queries=("CNN pruning",))


@pytest.mark.asyncio
async def test_external_research_executes_only_selected_provider_tools():
    class RecordingSearchService(AgentExternalResearchService):
        def __init__(self):
            super().__init__()
            self.called_tools = []

        async def _search_web(self, query):
            self.called_tools.append(("web", query))
            return [
                ExternalResearchDocument(
                    title="Web result",
                    url="https://example.com/web",
                    snippet="Web snippet",
                    source="web",
                )
            ]

        async def _search_papers(self, query):
            self.called_tools.append(("paper", query))
            return [
                ExternalResearchDocument(
                    title="Paper result",
                    url="https://example.com/paper",
                    snippet="Paper snippet",
                    source="paper",
                )
            ]

    service = RecordingSearchService()

    documents = await service._act(SearchPlan(tools=("web",), queries=("CNN",)))

    assert [document.source for document in documents] == ["web"]
    assert service.called_tools == [("web", "CNN")]


def test_external_citation_manager_dedupes_and_keeps_provider_rank_order():
    manager = ExternalCitationManager(top_k=3)
    documents = [
        ExternalResearchDocument(
            title="First provider result",
            url="https://example.com/first?utm_source=test",
            snippet="First snippet",
            source="web",
        ),
        ExternalResearchDocument(
            title="Duplicate URL with later provider rank",
            url="https://example.com/first",
            snippet="Duplicate snippet",
            source="web",
        ),
        ExternalResearchDocument(
            title="Paper Title",
            url="https://arxiv.org/abs/1",
            snippet="Paper snippet",
            source="paper",
        ),
        ExternalResearchDocument(
            title="Paper title",
            url="https://arxiv.org/abs/1v2",
            snippet="Duplicate paper snippet",
            source="paper",
        ),
    ]

    selected = manager.select_sources(documents)

    assert [document.title for document in selected] == [
        "First provider result",
        "Paper Title",
    ]


def test_external_citation_manager_drops_invalid_citation_markers():
    manager = ExternalCitationManager()
    citations = [
        AgentCitation(
            canonical_unit_id="external::web::1",
            course_id="WEB",
            unit_name="Convolutional neural network",
            learn_href="https://example.com/cnn",
            quote="A convolutional neural network is a neural network for visual imagery.",
            source="web",
        )
    ]

    answer = manager.render_answer(
        "CNN is commonly used for image data. [1] This unsupported claim cites nowhere. [9]",
        citations,
    )

    assert "[1](https://example.com/cnn)" in answer
    assert "[9]" not in answer


def test_external_research_adds_first_source_marker_when_answer_omits_citations():
    service = AgentExternalResearchService()
    citations = [
        AgentCitation(
            canonical_unit_id="external::web::1",
            course_id="WEB",
            unit_name="Convolutional neural network",
            learn_href="https://example.com/cnn",
            quote="A convolutional neural network is a neural network for visual imagery.",
            source="web",
        )
    ]

    answer = service._with_numeric_source_links(
        "CNN is a neural network architecture commonly used for images.",
        citations,
    )

    assert "[1](https://example.com/cnn)" in answer
