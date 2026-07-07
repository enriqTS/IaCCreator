"""Session management service for anonymous user sessions."""

import uuid

from app.persistence.base import AbstractRepository
from app.persistence.models import UserRecord


class SessionManager:
    """Manages session lifecycle: creation, resolution, and activity tracking.

    Takes an AbstractRepository as a constructor dependency so the service
    remains decoupled from the underlying storage backend.
    """

    def __init__(self, repo: AbstractRepository) -> None:
        self.repo = repo

    def create_session(self) -> str:
        """Generate a UUID v4 session ID, create a UserRecord, and return the session_id."""
        session_id = str(uuid.uuid4())
        self.repo.create_user(session_id)
        return session_id

    def resolve_session(self, session_id: str) -> UserRecord | None:
        """Look up a session by ID. Returns the UserRecord or None if not found."""
        return self.repo.get_user(session_id)

    def touch_session(self, session_id: str) -> None:
        """Update the last_active timestamp on the session's UserRecord."""
        self.repo.update_user_last_active(session_id)
