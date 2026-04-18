import json
from pathlib import Path
from urllib.parse import quote

import pytest


def _first_cs231n_video_path() -> str:
    units = json.loads(Path("data/course_bootstrap/units.json").read_text(encoding="utf-8"))
    unit = next(unit for unit in units if unit["course_slug"] == "cs231n" and unit.get("video_filename"))
    return f"/data/CS231n/videos/{quote(unit['video_filename'])}"


@pytest.mark.asyncio
async def test_learning_unit_endpoint_requires_authentication(client):
    response = await client.get("/api/courses/cs231n/units/lecture-1-introduction")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_video_asset_requires_authentication(client):
    response = await client.get(_first_cs231n_video_path())

    assert response.status_code == 401
