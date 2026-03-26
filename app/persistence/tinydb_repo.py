"""TinyDB implementation of the AbstractRepository interface."""

import os
import uuid
from datetime import datetime, timezone

from tinydb import TinyDB, where

from app.persistence.base import AbstractRepository
from app.persistence.models import DiagramRecord, DiagramSummary, UserRecord

_DEFAULT_DB_PATH = os.path.join("data", "db.json")


class TinyDBRepository(AbstractRepository):
    """Repository backed by a local TinyDB JSON file.

    Uses two tables – ``users`` and ``diagrams`` – inside a single JSON file
    (default ``data/db.json``).
    """

    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or _DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._db = TinyDB(path)
        self._users = self._db.table("users")
        self._diagrams = self._db.table("diagrams")

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    def create_user(self, session_id: str) -> UserRecord:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "session_id": session_id,
            "created_at": now,
            "last_active": now,
        }
        self._users.insert(doc)
        return UserRecord(**doc)

    def get_user(self, session_id: str) -> UserRecord | None:
        result = self._users.search(where("session_id") == session_id)
        if not result:
            return None
        return UserRecord(**result[0])

    def update_user_last_active(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._users.update(
            {"last_active": now},
            where("session_id") == session_id,
        )

    # ------------------------------------------------------------------
    # Diagram operations
    # ------------------------------------------------------------------

    def save_diagram(self, session_id: str, diagram: dict) -> str:
        diagram_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "diagram_id": diagram_id,
            "session_id": session_id,
            "project_name": diagram.get("projectName", ""),
            "diagram_state": diagram,
            "created_at": now,
            "updated_at": now,
        }
        self._diagrams.insert(doc)
        return diagram_id

    def get_diagram(self, diagram_id: str) -> DiagramRecord | None:
        result = self._diagrams.search(where("diagram_id") == diagram_id)
        if not result:
            return None
        return DiagramRecord(**result[0])

    def list_diagrams(self, session_id: str) -> list[DiagramSummary]:
        results = self._diagrams.search(where("session_id") == session_id)
        return [
            DiagramSummary(
                diagram_id=r["diagram_id"],
                project_name=r["project_name"],
                updated_at=r["updated_at"],
            )
            for r in results
        ]

    def update_diagram(self, diagram_id: str, diagram: dict) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        updated = self._diagrams.update(
            {
                "diagram_state": diagram,
                "project_name": diagram.get("projectName", ""),
                "updated_at": now,
            },
            where("diagram_id") == diagram_id,
        )
        return len(updated) > 0

    def delete_diagram(self, diagram_id: str) -> bool:
        removed = self._diagrams.remove(where("diagram_id") == diagram_id)
        return len(removed) > 0
