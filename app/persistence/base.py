"""Abstract repository interface for the persistence layer."""

from abc import ABC, abstractmethod

from app.persistence.models import DiagramRecord, DiagramSummary, UserRecord


class AbstractRepository(ABC):
    """Abstract base class defining the persistence layer interface.

    All persistence backends (TinyDB, DynamoDB) must implement this interface,
    ensuring the Session Manager and API endpoints remain decoupled from the
    storage mechanism.
    """

    # User operations

    @abstractmethod
    def create_user(self, session_id: str) -> UserRecord:
        """Create a new user record for the given session ID."""
        ...

    @abstractmethod
    def get_user(self, session_id: str) -> UserRecord | None:
        """Look up a user by session ID. Returns None if not found."""
        ...

    @abstractmethod
    def update_user_last_active(self, session_id: str) -> None:
        """Update the last-active timestamp on the user record."""
        ...

    # Diagram operations

    @abstractmethod
    def save_diagram(self, session_id: str, diagram: dict) -> str:
        """Save a new diagram and return the assigned diagram ID."""
        ...

    @abstractmethod
    def get_diagram(self, diagram_id: str) -> DiagramRecord | None:
        """Load a diagram by ID. Returns None if not found."""
        ...

    @abstractmethod
    def list_diagrams(self, session_id: str) -> list[DiagramSummary]:
        """List diagram summaries for a given session."""
        ...

    @abstractmethod
    def update_diagram(self, diagram_id: str, diagram: dict) -> bool:
        """Update an existing diagram. Returns True if found and updated."""
        ...

    @abstractmethod
    def delete_diagram(self, diagram_id: str) -> bool:
        """Delete a diagram by ID. Returns True if found and deleted."""
        ...
