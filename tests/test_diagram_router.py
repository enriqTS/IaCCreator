"""Unit tests for the diagram CRUD router.

Validates 404 for non-existent diagram IDs, 403 for cross-session access,
and 204 on successful delete using a real TinyDB backend with the full
middleware stack (session middleware + diagram router).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.session_middleware import COOKIE_NAME, SessionMiddleware
from app.persistence.tinydb_repo import TinyDBRepository
from app.routers.diagrams import get_repo, router as diagram_router
from app.services.session_manager import SessionManager

# A minimal valid diagram payload for creating/updating diagrams.
VALID_DIAGRAM = {
    "version": 1,
    "projectName": "test-project",
    "environments": [{"name": "dev", "variables": {}}],
    "elements": [
        {"id": "e1", "type": "lambda", "x": 0.0, "y": 0.0, "name": "fn1"}
    ],
    "connectors": [],
    "viewport": {"x": 0.0, "y": 0.0, "zoom": 1.0},
}


def _build_app(repo: TinyDBRepository) -> FastAPI:
    """Wire up a test FastAPI app with session middleware and diagram router."""
    manager = SessionManager(repo)
    app = FastAPI()
    app.dependency_overrides[get_repo] = lambda: repo
    app.add_middleware(SessionMiddleware, session_manager=manager)
    app.include_router(diagram_router)
    return app


@pytest.fixture()
def setup(tmp_path):
    """Provide a TestClient backed by a temporary TinyDB file."""
    db_path = str(tmp_path / "test_db.json")
    repo = TinyDBRepository(db_path=db_path)
    app = _build_app(repo)
    client = TestClient(app)
    yield client, repo
    repo._db.close()


# ---------------------------------------------------------------------------
# 404 for non-existent diagram IDs
# Requirements 3.4, 4.4, 5.3
# ---------------------------------------------------------------------------


class TestNotFoundForNonExistentDiagram:
    """GET, PUT, DELETE on a non-existent diagram_id must return 404."""

    def _make_client(self, setup_tuple):
        """Create a fresh TestClient with its own cookie jar."""
        _, repo = setup_tuple
        return TestClient(_build_app(repo))

    def test_get_nonexistent_returns_404(self, setup):
        """Validates: Requirement 4.4"""
        client = self._make_client(setup)
        # First request establishes a session (cookie stored in jar)
        client.get("/api/diagrams")

        resp = client.get("/api/diagrams/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Diagram not found"

    def test_put_nonexistent_returns_404(self, setup):
        """Validates: Requirement 3.4"""
        client = self._make_client(setup)
        client.get("/api/diagrams")

        resp = client.put("/api/diagrams/nonexistent-id", json=VALID_DIAGRAM)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Diagram not found"

    def test_delete_nonexistent_returns_404(self, setup):
        """Validates: Requirement 5.3"""
        client = self._make_client(setup)
        client.get("/api/diagrams")

        resp = client.delete("/api/diagrams/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Diagram not found"


# ---------------------------------------------------------------------------
# 403 for cross-session access
# Requirements 3.3, 4.3, 5.2
# ---------------------------------------------------------------------------


class TestForbiddenForCrossSessionAccess:
    """GET, PUT, DELETE on a diagram owned by another session must return 403."""

    def _setup_two_sessions(self, setup_tuple):
        """Create two distinct sessions and a diagram owned by the first.

        Uses two separate TestClient instances so each gets its own cookie jar,
        avoiding the deprecated per-request cookies= parameter.
        """
        _client, repo = setup_tuple
        app = _build_app(repo)

        # Session A: create a diagram
        client_a = TestClient(app)
        resp_a = client_a.post("/api/diagrams", json=VALID_DIAGRAM)
        assert resp_a.status_code == 200
        diagram_id = resp_a.json()["id"]

        # Session B: separate client → gets its own session
        client_b = TestClient(app)
        resp_b = client_b.get("/api/diagrams")
        assert resp_b.status_code == 200

        return diagram_id, client_a, client_b

    def test_get_cross_session_returns_403(self, setup):
        """Validates: Requirement 4.3"""
        diagram_id, _client_a, client_b = self._setup_two_sessions(setup)

        resp = client_b.get(f"/api/diagrams/{diagram_id}")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Forbidden"

    def test_put_cross_session_returns_403(self, setup):
        """Validates: Requirement 3.3"""
        diagram_id, _client_a, client_b = self._setup_two_sessions(setup)

        resp = client_b.put(
            f"/api/diagrams/{diagram_id}",
            json=VALID_DIAGRAM,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Forbidden"

    def test_delete_cross_session_returns_403(self, setup):
        """Validates: Requirement 5.2"""
        diagram_id, _client_a, client_b = self._setup_two_sessions(setup)

        resp = client_b.delete(f"/api/diagrams/{diagram_id}")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Forbidden"


# ---------------------------------------------------------------------------
# 204 on successful delete
# Requirement 5.1
# ---------------------------------------------------------------------------


class TestSuccessfulDelete:
    """DELETE on an owned diagram must return 204 with no body."""

    def _make_client(self, setup_tuple):
        """Create a fresh TestClient with its own cookie jar."""
        _, repo = setup_tuple
        return TestClient(_build_app(repo))

    def test_delete_own_diagram_returns_204(self, setup):
        """Validates: Requirement 5.1"""
        client = self._make_client(setup)

        # Create a diagram (establishes session via cookie jar)
        resp = client.post("/api/diagrams", json=VALID_DIAGRAM)
        diagram_id = resp.json()["id"]

        # Delete it
        resp = client.delete(f"/api/diagrams/{diagram_id}")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_deleted_diagram_returns_404_on_subsequent_get(self, setup):
        """After deletion, GET on the same ID must return 404."""
        client = self._make_client(setup)

        resp = client.post("/api/diagrams", json=VALID_DIAGRAM)
        diagram_id = resp.json()["id"]

        # Delete
        client.delete(f"/api/diagrams/{diagram_id}")

        # Verify it's gone
        resp = client.get(f"/api/diagrams/{diagram_id}")
        assert resp.status_code == 404
