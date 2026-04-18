"""
tests/test_exception_handlers.py
---------------------------------
RED phase: Verify DomainError subclasses được handler map đúng HTTP status codes.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from src.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
    ConflictError,
    ForbiddenError,
    InsufficientDataError,
)
from src.exception_handlers import domain_exception_handler


# ---------------------------------------------------------------------------
# Mini test app — chỉ dùng để test handler, không cần full app
# ---------------------------------------------------------------------------

test_app = FastAPI()
test_app.add_exception_handler(DomainError, domain_exception_handler)


@test_app.get("/not-found")
async def raise_not_found():
    raise NotFoundError("Topic không tồn tại")


@test_app.get("/validation")
async def raise_validation():
    raise ValidationError("Input không hợp lệ")


@test_app.get("/conflict")
async def raise_conflict():
    raise ConflictError("Session đã tồn tại")


@test_app.get("/forbidden")
async def raise_forbidden():
    raise ForbiddenError("Không có quyền")


@test_app.get("/insufficient")
async def raise_insufficient():
    raise InsufficientDataError("Chưa đủ dữ liệu")


@pytest_asyncio.fixture
async def test_client():
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_not_found_error_returns_404(test_client):
    response = await test_client.get("/not-found")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "Topic không tồn tại" in body["detail"]


@pytest.mark.asyncio
async def test_validation_error_returns_422(test_client):
    response = await test_client.get("/validation")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_conflict_error_returns_409(test_client):
    response = await test_client.get("/conflict")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_forbidden_error_returns_403(test_client):
    response = await test_client.get("/forbidden")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_insufficient_data_error_returns_409(test_client):
    response = await test_client.get("/insufficient")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_domain_error_subclass_hierarchy():
    """Mọi custom exception đều là subclass của DomainError."""
    assert issubclass(NotFoundError, DomainError)
    assert issubclass(ValidationError, DomainError)
    assert issubclass(ConflictError, DomainError)
    assert issubclass(ForbiddenError, DomainError)
    assert issubclass(InsufficientDataError, DomainError)


def test_domain_errors_have_status_code():
    """Mỗi DomainError subclass phải có status_code."""
    assert NotFoundError.status_code == 404
    assert ValidationError.status_code == 422
    assert ConflictError.status_code == 409
    assert ForbiddenError.status_code == 403
    assert InsufficientDataError.status_code == 409
