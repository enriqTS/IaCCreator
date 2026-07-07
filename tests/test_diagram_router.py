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
from app.persistence.models import DiagramRecord
from app.routers.diagrams import get_repo, verify_ownership, router as diagram_router
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


# ---------------------------------------------------------------------------
# verify_ownership dependency override
# Requirements 5.4, 5.6
# ---------------------------------------------------------------------------


class TestVerifyOwnershipOverride:
    """Overriding verify_ownership via app.dependency_overrides bypasses real repo lookup."""

    def test_override_verify_ownership_returns_fake_record(self, setup, tmp_path):
        """Validates: Requirement 5.6 — ownership override skips real repository."""
        _, repo = setup
        app = _build_app(repo)

        # Create a fake DiagramRecord that the override will return
        fake_record = DiagramRecord(
            diagram_id="fake-id",
            session_id="fake-session",
            project_name="override-project",
            diagram_state={"version": 1, "override": True},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Override verify_ownership to always return the fake record
        app.dependency_overrides[verify_ownership] = lambda: fake_record

        client = TestClient(app)
        # GET on any diagram_id should succeed and return the fake state
        resp = client.get("/api/diagrams/any-id-doesnt-matter")
        assert resp.status_code == 200
        assert resp.json() == {"version": 1, "override": True}

        # Clean up override
        del app.dependency_overrides[verify_ownership]

    def test_override_verify_ownership_independent_of_repo_override(self, setup, tmp_path):
        """Validates: Requirement 5.4, 5.6 — ownership and repo overrides are independent."""
        _, repo = setup
        app = _build_app(repo)

        fake_record = DiagramRecord(
            diagram_id="independent-id",
            session_id="independent-session",
            project_name="independent-project",
            diagram_state={"version": 2, "independent": True},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Override ONLY verify_ownership, not get_repo
        # This proves the ownership check can be overridden separately
        app.dependency_overrides[verify_ownership] = lambda: fake_record

        client = TestClient(app)

        # GET should return fake record without touching the repo for ownership
        resp = client.get("/api/diagrams/does-not-exist-in-repo")
        assert resp.status_code == 200
        assert resp.json() == {"version": 2, "independent": True}

        # PUT should also work — repo override still used for update_diagram
        updated_payload = {
            "version": 3,
            "projectName": "updated",
            "environments": [],
            "elements": [],
            "connectors": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        resp = client.put("/api/diagrams/independent-id", json=updated_payload)
        assert resp.status_code == 200
        assert resp.json()["id"] == "independent-id"

        del app.dependency_overrides[verify_ownership]
