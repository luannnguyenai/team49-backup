import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app


pytestmark = pytest.mark.anyio


async def test_course_sections_endpoint_returns_canonical_field_names():
    section_id = uuid.uuid4()
    course_id = uuid.uuid4()
    expected = [
        {
            "id": str(section_id),
            "course_id": str(course_id),
            "canonical_course_id": "course_cs231n",
            "title": "Foundations",
            "description": "Core section",
            "order_index": 1,
            "prerequisite_section_ids": None,
            "learning_units_count": 2,
        }
    ]

    with patch(
        "src.routers.content.list_course_sections",
        new=AsyncMock(return_value=expected),
        create=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/api/course-sections")

    assert response.status_code == 200
    assert response.json() == expected


async def test_course_section_detail_endpoint_returns_learning_units():
    section_id = uuid.uuid4()
    course_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    now = datetime.now(UTC)
    expected = {
        "id": str(section_id),
        "course_id": str(course_id),
        "canonical_course_id": "course_cs231n",
        "title": "Foundations",
        "description": "Core section",
        "order_index": 1,
        "prerequisite_section_ids": None,
        "learning_units_count": 1,
        "learning_units": [
            {
                "id": str(unit_id),
                "canonical_unit_id": "local::lecture01::seg1",
                "title": "Vectors",
                "description": None,
                "order_index": 1,
                "estimated_hours_beginner": 1.0,
                "estimated_hours_intermediate": 1.0,
            }
        ],
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }

    with patch(
        "src.routers.content.get_course_section_detail",
        new=AsyncMock(return_value=expected),
        create=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(f"/api/course-sections/{section_id}")

    assert response.status_code == 200
    assert response.json()["learning_units"][0]["title"] == "Vectors"
    assert "topics" not in response.json()


async def test_learning_unit_content_endpoint_returns_canonical_field_names():
    section_id = uuid.uuid4()
    unit_id = uuid.uuid4()
    expected = {
        "learning_unit_id": str(unit_id),
        "title": "Vectors",
        "section_id": str(section_id),
        "section_title": "Foundations",
        "content_markdown": "Summary",
        "video_url": None,
    }

    with patch(
        "src.routers.content.get_learning_unit_content",
        new=AsyncMock(return_value=expected),
        create=True,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(f"/api/learning-units/{unit_id}/content")

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    "path",
    [
        "/api/modules",
        f"/api/modules/{uuid.uuid4()}",
        f"/api/topics/{uuid.uuid4()}",
        f"/api/topics/{uuid.uuid4()}/content",
        "/api/seed",
    ],
)
async def test_legacy_module_topic_routes_are_removed(path):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.post(path) if path == "/api/seed" else await client.get(path)

    assert response.status_code == 404
