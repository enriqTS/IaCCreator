"""Repository factory — selects the persistence backend at runtime."""

import os

from app.persistence.base import AbstractRepository


def get_repository() -> AbstractRepository:
    """Return the appropriate repository based on the PERSISTENCE_BACKEND env var.

    Supported values: ``tinydb`` (default), ``dynamodb``.
    """
    backend = os.getenv("PERSISTENCE_BACKEND", "tinydb").lower()

    if backend == "dynamodb":
        from app.persistence.dynamodb_repo import DynamoDBRepository

        return DynamoDBRepository()

    if backend == "tinydb":
        from app.persistence.tinydb_repo import TinyDBRepository

        return TinyDBRepository()

    raise ValueError(
        f"Unknown PERSISTENCE_BACKEND: {backend!r}. Expected 'tinydb' or 'dynamodb'."
    )
