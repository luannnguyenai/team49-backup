"""
exception_handlers.py
---------------------
FastAPI exception handlers — register in app.py via:
    app.add_exception_handler(DomainError, domain_exception_handler)
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from src.exceptions import DomainError


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map DomainError (and subclasses) to the appropriate HTTP status code."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )
