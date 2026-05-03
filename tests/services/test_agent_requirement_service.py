from types import SimpleNamespace

import pytest

from src.schemas.agent import PathRequirementsRequest, RuntimeNavigationTrace
from src.services.agent_requirement_service import AgentPathRequirementService


class FakeNavigation:
    async def resolve_many(self, canonical_unit_ids):
        return {
            unit_id: SimpleNamespace(
                canonical_unit_id=unit_id,
                learn_href=f"/courses/cs230/learn/{unit_id}",
            )
            for unit_id in canonical_unit_ids
        }

    def to_trace(self, nav):
        return RuntimeNavigationTrace(
            canonical_unit_id=nav.canonical_unit_id,
            source="product_learning_unit",
            learn_href=nav.learn_href,
        )


@pytest.mark.asyncio
async def test_path_requirements_use_canonical_course_id_content_policy_and_mastery_overlay():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit):
            assert course_ids == ["CS224n"]
            return [
                SimpleNamespace(unit_id="target-nlp", course_id="CS224n"),
            ]

        async def get_unit_kp_rows(self, unit_ids):
            return [SimpleNamespace(unit_id="target-nlp", kp_id="kp-target", planner_role="main")]

        async def get_prerequisite_edges_for_kps(self, kp_ids):
            return [SimpleNamespace(source_kp_id="kp-prereq", target_kp_id="kp-target")]

        async def get_unit_kp_rows_by_kp_ids(self, kp_ids):
            return [
                SimpleNamespace(unit_id="good-dl", kp_id="kp-prereq", planner_role="prereq"),
                SimpleNamespace(unit_id="career-dl", kp_id="kp-prereq", planner_role="prereq"),
            ]

        async def get_canonical_units_by_ids(self, unit_ids):
            return {
                "good-dl": SimpleNamespace(
                    unit_id="good-dl",
                    course_id="CS230",
                    unit_name="Backpropagation",
                    active=True,
                    section_flags=[],
                    content_type="concept",
                    is_worth_learning=True,
                ),
                "career-dl": SimpleNamespace(
                    unit_id="career-dl",
                    course_id="CS230",
                    unit_name="Career advice",
                    active=True,
                    section_flags=["career"],
                    content_type="concept",
                    is_worth_learning=True,
                ),
            }

        async def get_mastery_lcb_by_kp_ids(self, user_id, kp_ids):
            assert str(user_id) == "user-1"
            return {"kp-prereq": 0.86}

    service = AgentPathRequirementService(Repo(), FakeNavigation())
    response = await service.get_requirements(
        PathRequirementsRequest(targetPathKey="nlp"),
        allowed_course_ids=["CS230", "CS224n"],
        user_id="user-1",
    )

    assert [unit.canonical_unit_id for unit in response.required_units] == ["good-dl"]
    assert response.required_units[0].course_id == "CS230"
    assert response.required_units[0].status == "already_mastered"
    assert response.required_units[0].mastery_lcb == 0.86


@pytest.mark.asyncio
async def test_path_requirements_respects_allowed_course_scope():
    class Repo:
        async def search_canonical_units(self, terms, course_ids, limit):
            return []

        async def get_unit_kp_rows(self, unit_ids):
            return []

        async def get_prerequisite_edges_for_kps(self, kp_ids):
            return []

        async def get_unit_kp_rows_by_kp_ids(self, kp_ids):
            return []

        async def get_canonical_units_by_ids(self, unit_ids):
            return {}

    service = AgentPathRequirementService(Repo(), FakeNavigation())
    response = await service.get_requirements(
        PathRequirementsRequest(targetPathKey="nlp"),
        allowed_course_ids=["CS230", "CS231n"],
        user_id="user-1",
    )

    assert response.required_units == []
    assert response.trace.candidate_courses == []
