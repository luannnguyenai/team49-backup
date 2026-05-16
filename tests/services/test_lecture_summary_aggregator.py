import pytest

from src.services.lecture_summary_aggregator import LectureSummaryAggregator


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeModel:
    def __init__(self, content):
        self._content = content
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        return _FakeResponse(self._content)


class _FailingModel:
    async def ainvoke(self, messages):
        raise RuntimeError("upstream model down")


@pytest.mark.asyncio
async def test_aggregate_returns_text_and_caches_by_content_hash():
    model = _FakeModel("Lecture overview text.")
    aggregator = LectureSummaryAggregator(model=model)
    units = [
        {"canonical_unit_id": "u1", "unit_name": "Seg 1", "summary": "First idea."},
        {"canonical_unit_id": "u2", "unit_name": "Seg 2", "summary": "Second idea."},
    ]

    first = await aggregator.aggregate(lecture_title="Lecture 2", units=units, language_hint="vi")
    second = await aggregator.aggregate(lecture_title="Lecture 2", units=units, language_hint="vi")

    assert first == "Lecture overview text."
    assert second == "Lecture overview text."
    assert model.calls == 1


@pytest.mark.asyncio
async def test_aggregate_returns_none_when_units_have_no_summary():
    model = _FakeModel("ignored")
    aggregator = LectureSummaryAggregator(model=model)
    units = [
        {"canonical_unit_id": "u1", "unit_name": "Seg 1"},
        {"canonical_unit_id": "u2", "unit_name": "Seg 2", "summary": "   "},
    ]

    result = await aggregator.aggregate(lecture_title="Lecture 2", units=units)

    assert result is None
    assert model.calls == 0


@pytest.mark.asyncio
async def test_aggregate_handles_list_content_payload():
    response_content = [{"type": "text", "text": "part 1"}, {"type": "text", "text": "part 2"}]
    aggregator = LectureSummaryAggregator(model=_FakeModel(response_content))

    result = await aggregator.aggregate(
        lecture_title="Lecture",
        units=[{"canonical_unit_id": "u1", "unit_name": "Seg 1", "summary": "Idea."}],
    )

    assert result == "part 1\npart 2"


@pytest.mark.asyncio
async def test_aggregate_returns_none_when_model_invocation_fails():
    aggregator = LectureSummaryAggregator(model=_FailingModel())

    result = await aggregator.aggregate(
        lecture_title="Lecture",
        units=[{"canonical_unit_id": "u1", "unit_name": "Seg 1", "summary": "Idea."}],
    )

    assert result is None


@pytest.mark.asyncio
async def test_aggregate_returns_none_when_model_returns_empty_string():
    aggregator = LectureSummaryAggregator(model=_FakeModel("   "))

    result = await aggregator.aggregate(
        lecture_title="Lecture",
        units=[{"canonical_unit_id": "u1", "unit_name": "Seg 1", "summary": "Idea."}],
    )

    assert result is None
