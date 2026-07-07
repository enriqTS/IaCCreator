"""FastAPI exception handlers translating domain errors to HTTP responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import DomainError


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Translate DomainError subclasses into HTTP 422 responses."""
    detail = str(exc)
    return JSONResponse(status_code=422, content={"detail": detail})
