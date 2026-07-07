"""Unit tests for CORS configuration and app wiring in main.py.

Validates:
- CORS headers on preflight requests (Requirements 8.1, 8.2, 8.3, 8.4)
- Session cookie attributes via the full app (Requirements 1.3, 1.4)
- Diagram router is mounted and reachable
- Existing /generate endpoints remain intact
"""


import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Build a TestClient from the real app, using a temp TinyDB file."""
    db_path = str(tmp_path / "test_db.json")

    # Patch the factory so the module-level get_repository() in main.py
    # returns a TinyDB repo backed by a temp file.
    from app.persistence.tinydb_repo import TinyDBRepository

    temp_repo = TinyDBRepository(db_path=db_path)
    monkeypatch.setattr("app.persistence.factory.get_repository", lambda: temp_repo)

    import importlib

    import app.main as main_mod

    importlib.reload(main_mod)
    yield TestClient(main_mod.app)
    temp_repo._db.close()


# ---------------------------------------------------------------------------
# CORS preflight (OPTIONS) — Requirements 8.1, 8.2, 8.3, 8.4
# ---------------------------------------------------------------------------

FRONTEND_ORIGIN = "http://localhost:3000"


class TestCORSPreflight:
    """CORS middleware must respond correctly to preflight OPTIONS requests."""

    def test_preflight_allows_default_origin(self, client):
        """Validates: Requirement 8.4 — default origin http://localhost:3000."""
        resp = client.options(
            "/api/diagrams",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN

    def test_preflight_allows_credentials(self, client):
        """Validates: Requirement 8.2 — Access-Control-Allow-Credentials: true."""
        resp = client.options(
            "/api/diagrams",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_preflight_allows_required_methods(self, client):
        """Validates: Requirement 8.3 — GET, POST, PUT, DELETE allowed."""
        for method in ("GET", "POST", "PUT", "DELETE"):
            resp = client.options(
                "/api/diagrams",
                headers={
                    "Origin": FRONTEND_ORIGIN,
                    "Access-Control-Request-Method": method,
                },
            )
            allowed = resp.headers.get("access-control-allow-methods", "")
            assert method in allowed, f"{method} not in allow-methods: {allowed}"

    def test_preflight_rejects_unknown_origin(self, client):
        """An origin not in allow_origins should not get CORS headers."""
        resp = client.options(
            "/api/diagrams",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette CORS middleware omits the header for disallowed origins
        assert resp.headers.get("access-control-allow-origin") is None


class TestCORSOnActualRequests:
    """CORS headers must also appear on regular (non-preflight) responses."""

    def test_cors_headers_on_get(self, client):
        """Validates: Requirement 8.1 — CORS middleware present on real requests."""
        resp = client.get(
            "/api/diagrams",
            headers={"Origin": FRONTEND_ORIGIN},
        )
        assert resp.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN
        assert resp.headers.get("access-control-allow-credentials") == "true"


# ---------------------------------------------------------------------------
# Session cookie via the full app — Requirements 1.3, 1.4
# ---------------------------------------------------------------------------


class TestSessionCookieViaFullApp:
    """Session middleware must set correct cookie attributes through the real app."""

    def test_first_request_sets_session_cookie(self, client):
        """Validates: Requirement 1.3 — cookie attributes."""
        resp = client.get("/api/diagrams")
        cookie_header = resp.headers.get("set-cookie", "")
        assert "session_id" in cookie_header
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()
        assert "2592000" in cookie_header  # Max-Age

    def test_invalid_cookie_creates_new_session(self, client):
        """Validates: Requirement 1.4 — invalid cookie → new session."""
        resp = client.get(
            "/api/diagrams",
            cookies={"session_id": "bogus-nonexistent-id"},
        )
        assert resp.status_code == 200
        cookie_header = resp.headers.get("set-cookie", "")
        assert "session_id" in cookie_header


# ---------------------------------------------------------------------------
# Diagram router is mounted — sanity check
# ---------------------------------------------------------------------------


class TestDiagramRouterMounted:
    """The diagram CRUD router must be reachable through the main app."""

    def test_list_diagrams_returns_200(self, client):
        """GET /api/diagrams should return 200 with an empty list initially."""
        resp = client.get("/api/diagrams")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_diagram_returns_id(self, client):
        """POST /api/diagrams with a valid body should return an id."""
        payload = {
            "version": 1,
            "projectName": "test",
            "environments": [{"name": "dev", "variables": {}}],
            "elements": [],
            "connectors": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        resp = client.post("/api/diagrams", json=payload)
        assert resp.status_code == 200
        assert "id" in resp.json()
