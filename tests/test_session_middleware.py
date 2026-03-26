"""Unit tests for the session middleware.

Validates cookie attributes, session resolution, and new-session creation
using a real TinyDB backend and the FastAPI TestClient.
"""

import os
import shutil
import tempfile

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.middleware.session_middleware import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    SessionMiddleware,
)
from app.persistence.tinydb_repo import TinyDBRepository
from app.services.session_manager import SessionManager


def _make_app(session_manager: SessionManager) -> FastAPI:
    """Build a minimal FastAPI app with the session middleware and a test route."""
    test_app = FastAPI()
    test_app.add_middleware(SessionMiddleware, session_manager=session_manager)

    @test_app.get("/test")
    async def _test_route(request: Request) -> JSONResponse:
        return JSONResponse({"session_id": request.state.session_id})

    return test_app


@pytest.fixture()
def _env(tmp_path):
    """Provide a SessionManager backed by a temporary TinyDB file."""
    db_path = str(tmp_path / "test_db.json")
    repo = TinyDBRepository(db_path=db_path)
    manager = SessionManager(repo)
    yield manager, repo
    repo._db.close()


class TestNewSessionCreation:
    """When no session cookie is present, the middleware must create one."""

    def test_response_sets_session_cookie(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        assert resp.status_code == 200

        # The response must contain a Set-Cookie header for session_id
        cookie_header = resp.headers.get("set-cookie", "")
        assert COOKIE_NAME in cookie_header

    def test_cookie_is_httponly(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        cookie_header = resp.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie_header

    def test_cookie_samesite_lax(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        cookie_header = resp.headers.get("set-cookie", "").lower()
        assert "samesite=lax" in cookie_header

    def test_cookie_path_root(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        cookie_header = resp.headers.get("set-cookie", "")
        assert "Path=/" in cookie_header or "path=/" in cookie_header.lower()

    def test_cookie_max_age(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        cookie_header = resp.headers.get("set-cookie", "")
        assert str(COOKIE_MAX_AGE) in cookie_header

    def test_session_id_attached_to_request_state(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get("/test")
        body = resp.json()
        assert "session_id" in body
        assert len(body["session_id"]) > 0


class TestExistingSessionResolution:
    """When a valid session cookie is present, the middleware must resolve it."""

    def test_valid_cookie_does_not_set_new_cookie(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        # First request — creates a session
        resp1 = client.get("/test")
        session_id = resp1.json()["session_id"]

        # Second request with the session cookie
        resp2 = client.get("/test", cookies={COOKIE_NAME: session_id})

        # Should NOT set a new cookie (session already exists)
        set_cookie = resp2.headers.get("set-cookie", "")
        assert COOKIE_NAME not in set_cookie

    def test_valid_cookie_resolves_same_session(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp1 = client.get("/test")
        session_id = resp1.json()["session_id"]

        resp2 = client.get("/test", cookies={COOKIE_NAME: session_id})
        assert resp2.json()["session_id"] == session_id


class TestInvalidCookieCreatesNewSession:
    """When the cookie references a non-existent session, treat as new."""

    def test_invalid_cookie_creates_new_session(self, _env):
        manager, _repo = _env
        app = _make_app(manager)
        client = TestClient(app)

        resp = client.get(
            "/test",
            cookies={COOKIE_NAME: "non-existent-session-id"},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["session_id"] != "non-existent-session-id"

        # A Set-Cookie header must be present for the new session
        cookie_header = resp.headers.get("set-cookie", "")
        assert COOKIE_NAME in cookie_header
