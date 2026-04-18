"""
exceptions.py
-------------
Domain exception hierarchy.
Services raise these; the exception handler in app.py maps them to HTTP responses.
Keeps HTTP concerns out of the business logic layer.
"""


class DomainError(Exception):
    """Base class for all domain exceptions. Router layer catches this."""
    status_code: int = 500


class NotFoundError(DomainError):
    """Resource does not exist (404)."""
    status_code = 404


class ValidationError(DomainError):
    """Input is semantically invalid (422)."""
    status_code = 422


class ConflictError(DomainError):
    """Resource already exists or state conflict (409)."""
    status_code = 409


class ForbiddenError(DomainError):
    """Caller lacks permission (403)."""
    status_code = 403


class InsufficientDataError(DomainError):
    """Not enough data to complete the operation (409)."""
    status_code = 409
