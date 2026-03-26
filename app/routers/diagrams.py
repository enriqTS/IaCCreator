"""Diagram CRUD router — RESTful endpoints scoped to the caller's session."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from app.models.diagram_models import DiagramStateInput
from app.persistence.base import AbstractRepository

router = APIRouter(prefix="/api/diagrams")

# Module-level repository reference, set during app startup.
_repo: AbstractRepository | None = None


def set_repository(repo: AbstractRepository) -> None:
    """Assign the repository instance used by all route handlers."""
    global _repo  # noqa: PLW0603
    _repo = repo


def _get_repo() -> AbstractRepository:
    """Return the repository or raise if it hasn't been configured."""
    if _repo is None:
        raise RuntimeError("Diagram router repository has not been initialised")
    return _repo


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def create_diagram(body: DiagramStateInput, request: Request):
    """Create a new diagram for the current session."""
    repo = _get_repo()
    session_id: str = request.state.session_id
    diagram_id = repo.save_diagram(session_id, body.model_dump())
    return {"id": diagram_id}


@router.get("")
async def list_diagrams(request: Request):
    """Return diagram summaries belonging to the current session."""
    repo = _get_repo()
    session_id: str = request.state.session_id
    summaries = repo.list_diagrams(session_id)
    return [s.model_dump() for s in summaries]


@router.get("/{diagram_id}")
async def get_diagram(diagram_id: str, request: Request):
    """Load the full diagram state by ID (ownership-checked)."""
    repo = _get_repo()
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return record.diagram_state


@router.put("/{diagram_id}")
async def update_diagram(diagram_id: str, body: DiagramStateInput, request: Request):
    """Update an existing diagram (ownership-checked)."""
    repo = _get_repo()
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    repo.update_diagram(diagram_id, body.model_dump())
    return {"id": diagram_id}


@router.delete("/{diagram_id}", status_code=204)
async def delete_diagram(diagram_id: str, request: Request):
    """Delete a diagram (ownership-checked). Returns 204 on success."""
    repo = _get_repo()
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    repo.delete_diagram(diagram_id)
    return Response(status_code=204)
