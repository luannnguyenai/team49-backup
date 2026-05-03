from types import SimpleNamespace

import pytest

from src.schemas.agent import RetrievalTrace, UnitSearchResponse, UnitSearchResult
from src.services.agent_graph_contracts import AgentSlots
from src.services.agent_slot_resolver import AgentSlotResolver


@pytest.mark.asyncio
async def test_content_rag_intents_do_not_block_on_canonical_ambiguity():
    async def search(request, allowed_course_ids):
        raise AssertionError("Content RAG should not pre-search during slot canonicalization")

    slots = await AgentSlotResolver(SimpleNamespace(search=search)).canonicalize(
        raw_slots=AgentSlots(raw_topic="attention mask"),
        intent="find_content",
        allowed_course_ids=["CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert slots.raw_topic == "attention mask"
    assert slots.ambiguity_options == []
    assert slots.resolved_search_path_ids == ["nlp"]


@pytest.mark.asyncio
async def test_assessment_intent_still_clarifies_ambiguous_units():
    async def search(request, allowed_course_ids):
        return UnitSearchResponse(
            results=[
                UnitSearchResult(
                    canonical_unit_id="unit-attention",
                    course_id="CS224n",
                    unit_name="Attention",
                    score=2,
                ),
                UnitSearchResult(
                    canonical_unit_id="unit-self-attention",
                    course_id="CS224n",
                    unit_name="Self Attention",
                    score=2,
                ),
            ],
            trace=RetrievalTrace(trace_id="trace-ambiguous", ranking_version="unit_search_v1"),
        )

    slots = await AgentSlotResolver(SimpleNamespace(search=search)).canonicalize(
        raw_slots=AgentSlots(raw_topic="attention"),
        intent="assess_knowledge",
        allowed_course_ids=["CS224n"],
        current_path_course_ids=["CS224n"],
    )

    assert [option["canonical_unit_id"] for option in slots.ambiguity_options] == [
        "unit-attention",
        "unit-self-attention",
    ]
