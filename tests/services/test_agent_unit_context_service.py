from types import SimpleNamespace

import pytest

from src.services.agent_unit_context_service import AgentUnitContextService


class FakeNavigation:
    async def resolve_many(self, canonical_unit_ids):
        return {
            canonical_unit_ids[0]: SimpleNamespace(
                learn_href=f"/courses/cs231n/learn/{canonical_unit_ids[0]}"
            )
        }


@pytest.mark.asyncio
async def test_unit_context_returns_navigation_kps_quiz_and_snippets():
    class Repo:
        async def get_canonical_units_by_ids(self, unit_ids):
            return {
                "unit-cnn": SimpleNamespace(
                    course_id="CS231n",
                    unit_name="Receptive fields",
                    summary="CNN receptive field summary",
                    description=None,
                    key_points=["kernels", "stride"],
                    has_quiz_items=False,
                )
            }

        async def get_unit_kp_rows(self, unit_ids):
            return [SimpleNamespace(kp_id="kp-rf")]

        async def get_quiz_item_counts_by_unit_ids(self, unit_ids):
            return {"unit-cnn": 2}

    context = await AgentUnitContextService(Repo(), FakeNavigation()).get_context(
        "unit-cnn",
        allowed_course_ids=["CS231n"],
    )

    assert context.learn_href == "/courses/cs231n/learn/unit-cnn"
    assert context.kp_ids == ["kp-rf"]
    assert context.quiz_available is True
    assert context.transcript_snippets[0]["text"] == "CNN receptive field summary"


@pytest.mark.asyncio
async def test_unit_context_enforces_allowed_course_scope():
    class Repo:
        async def get_canonical_units_by_ids(self, unit_ids):
            return {
                "unit-nlp": SimpleNamespace(
                    course_id="CS224n",
                    unit_name="Word vectors",
                    summary="Embedding summary",
                    description=None,
                    key_points=[],
                    has_quiz_items=False,
                )
            }

    service = AgentUnitContextService(Repo(), FakeNavigation())

    with pytest.raises(PermissionError):
        await service.get_transcript_snippets("unit-nlp", allowed_course_ids=["CS231n"])
