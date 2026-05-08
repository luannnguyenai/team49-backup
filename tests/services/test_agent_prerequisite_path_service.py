from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.services.agent_prerequisite_path_service import AgentPrerequisitePathService


class FakeNavigationService:
    async def resolve_many(self, canonical_unit_ids):
        return {
            unit_id: SimpleNamespace(learn_href=f"/learn/{unit_id.replace(':', '-')}")
            for unit_id in canonical_unit_ids
        }


class FakeRepo:
    def __init__(self):
        self.learning_unit_ids = {
            "unit-prereq": uuid4(),
            "unit-target": uuid4(),
        }

    async def get_canonical_units_by_ids(self, canonical_unit_ids):
        units = {
            "unit-prereq": SimpleNamespace(
                unit_id="unit-prereq",
                course_id="CS231n",
                unit_name="Object detection foundations",
                active=True,
                section_flags=[],
                content_type="core",
                is_worth_learning=True,
            ),
            "unit-target": SimpleNamespace(
                unit_id="unit-target",
                course_id="CS231n",
                unit_name="Mask R-CNN instance segmentation",
                active=True,
                section_flags=[],
                content_type="core",
                is_worth_learning=True,
            ),
        }
        return {unit_id: units[unit_id] for unit_id in canonical_unit_ids if unit_id in units}

    async def get_unit_kp_rows(self, canonical_unit_ids):
        rows = {
            "unit-target": [SimpleNamespace(unit_id="unit-target", kp_id="kp-target")],
            "unit-prereq": [SimpleNamespace(unit_id="unit-prereq", kp_id="kp-prereq")],
        }
        return [row for unit_id in canonical_unit_ids for row in rows.get(unit_id, [])]

    async def get_prerequisite_edges_for_kps(self, kp_ids):
        return [
            SimpleNamespace(
                source_kp_id="kp-prereq",
                target_kp_id="kp-target",
                active=True,
            )
        ]

    async def get_unit_kp_rows_by_kp_ids(self, kp_ids):
        if "kp-prereq" not in kp_ids:
            return []
        return [SimpleNamespace(unit_id="unit-prereq", kp_id="kp-prereq")]

    async def get_concepts_by_ids(self, kp_ids):
        return {
            "kp-prereq": SimpleNamespace(name="Object detection"),
            "kp-target": SimpleNamespace(name="Mask prediction"),
        }

    async def get_mastery_lcb_by_kp_ids(self, user_id, kp_ids):
        return {"kp-prereq": 0.92}

    async def get_user_learning_status_by_canonical_ids(self, user_id, canonical_unit_ids):
        return {
            "unit-prereq": "skipped",
            "unit-target": "not_started",
        }


@pytest.mark.asyncio
async def test_prerequisite_path_keeps_skipped_prerequisite_and_target_in_order():
    service = AgentPrerequisitePathService(FakeRepo(), FakeNavigationService())

    path = await service.build(
        target_canonical_unit_id="unit-target",
        allowed_course_ids=["CS231n"],
        user_id=UUID("f2a9c00c-0a62-56cc-895d-5ab78de222f8"),
    )

    assert path is not None
    assert path.target_canonical_unit_id == "unit-target"
    assert [node.canonical_unit_id for node in path.nodes] == ["unit-prereq", "unit-target"]
    assert path.nodes[0].role == "prerequisite"
    assert path.nodes[0].status == "skipped"
    assert path.nodes[1].role == "target"
    assert path.edges[0].from_canonical_unit_id == "unit-prereq"
    assert path.edges[0].to_canonical_unit_id == "unit-target"
    assert "Object detection" in (path.edges[0].reason or "")
