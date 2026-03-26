"""Persistence layer: abstract repository interface and data models."""

from app.persistence.base import AbstractRepository
from app.persistence.factory import get_repository
from app.persistence.models import DiagramRecord, DiagramSummary, UserRecord

__all__ = [
    "AbstractRepository",
    "DiagramRecord",
    "DiagramSummary",
    "UserRecord",
    "get_repository",
]
