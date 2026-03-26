"""Middleware package for the FastAPI application."""

from app.middleware.session_middleware import SessionMiddleware

__all__ = ["SessionMiddleware"]
