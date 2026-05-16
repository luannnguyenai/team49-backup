from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from src.repositories.canonical_content_repo import CanonicalContentRepository


@pytest.mark.asyncio
async def test_get_linked_learning_units_skips_empty_course_ids():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_linked_learning_units([]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_get_unit_kp_rows_executes_query():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    rows = await repo.get_unit_kp_rows(["unit-a"])

    assert rows == []
    assert session.execute.await_count == 1


@pytest.mark.asyncio
async def test_get_prerequisite_edges_skips_empty_kps():
    session = AsyncMock()
    repo = CanonicalContentRepository(session)

    assert await repo.get_prerequisite_edges_for_kps([]) == []
    assert session.execute.await_count == 0


@pytest.mark.asyncio
async def test_search_canonical_units_casts_json_section_flags_before_like():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    await repo.search_canonical_units(["cnn"], ["CS230"])

    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "CAST(units.section_flags AS VARCHAR) NOT LIKE" in compiled


@pytest.mark.asyncio
async def test_search_canonical_units_matches_mixed_case_course_ids_case_insensitively():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    await repo.search_canonical_units(["unet"], ["CS231n"])

    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "lower(units.course_id) IN" in compiled


@pytest.mark.asyncio
async def test_search_canonical_units_title_only_excludes_body_fields():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    await repo.search_canonical_units(["yolo"], ["CS231n"], title_only=True)

    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "units.unit_name" in compiled
    assert "units.lecture_title" in compiled
    assert "lower(coalesce(units.summary" not in compiled
    assert "lower(coalesce(units.description" not in compiled


@pytest.mark.asyncio
async def test_get_linked_learning_units_orders_by_course_section_then_unit():
    session = AsyncMock()
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repo = CanonicalContentRepository(session)

    await repo.get_linked_learning_units(["CS224n"])

    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "JOIN course_sections" in compiled
    assert "ORDER BY courses.sort_order, course_sections.sort_order, learning_units.sort_order" in compiled


@pytest.mark.asyncio
async def test_get_lecture_context_accepts_allowed_course_uuid_scope():
    session = AsyncMock()
    course_id = uuid4()
    current_unit = SimpleNamespace(
        unit_id="cs230::lecture-2::seg3",
        course_id="CS230",
        lecture_id="lecture-2",
        lecture_title="Lecture 2",
        lecture_order=2,
        unit_name="Neurons, multi-class labels, capacity, and embeddings",
        summary="Unit summary",
        description="Unit description",
        duration_min=8,
        ordering_index=3,
    )
    course = SimpleNamespace(
        id=course_id,
        canonical_course_id="CS230",
        slug="cs230",
    )

    current_result = Mock()
    current_result.scalar_one_or_none.return_value = current_unit
    course_result = Mock()
    course_result.scalars.return_value.all.return_value = [course]
    lecture_result = Mock()
    lecture_result.scalar_one_or_none.return_value = None
    units_result = Mock()
    units_result.scalars.return_value.all.return_value = [current_unit]
    session.execute.side_effect = [
        current_result,
        course_result,
        lecture_result,
        units_result,
    ]
    repo = CanonicalContentRepository(session)

    context = await repo.get_lecture_context_for_unit(
        "cs230::lecture-2::seg3",
        allowed_course_ids=[str(course_id)],
    )

    assert context is not None
    assert context["course_id"] == "CS230"
    assert context["units"][0]["canonical_unit_id"] == "cs230::lecture-2::seg3"
