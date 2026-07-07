"""Diagram CRUD router — RESTful endpoints scoped to the caller's session."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.models.diagram_models import DiagramStateInput
from app.persistence.base import AbstractRepository
from app.persistence.factory import get_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/diagrams")


def get_repo() -> AbstractRepository:
    """Repository dependency — overridable via app.dependency_overrides."""
    return get_repository()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def create_diagram(
    body: DiagramStateInput,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
):
    """Create a new diagram for the current session."""
    session_id: str = request.state.session_id
    diagram_id = repo.save_diagram(session_id, body.model_dump())
    logger.info(
        "Diagram created",
        extra={"correlation_id": session_id, "diagram_id": diagram_id},
    )
    return {"id": diagram_id}


@router.get("")
async def list_diagrams(
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
):
    """Return diagram summaries belonging to the current session."""
    session_id: str = request.state.session_id
    summaries = repo.list_diagrams(session_id)
    logger.info(
        "Diagrams listed",
        extra={"correlation_id": session_id},
    )
    return [s.model_dump() for s in summaries]


@router.get("/{diagram_id}")
async def get_diagram(
    diagram_id: str,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
):
    """Load the full diagram state by ID (ownership-checked)."""
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    logger.info(
        "Diagram retrieved",
        extra={"correlation_id": session_id, "diagram_id": diagram_id},
    )
    return record.diagram_state


@router.put("/{diagram_id}")
async def update_diagram(
    diagram_id: str,
    body: DiagramStateInput,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
):
    """Update an existing diagram (ownership-checked)."""
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    repo.update_diagram(diagram_id, body.model_dump())
    logger.info(
        "Diagram updated",
        extra={"correlation_id": session_id, "diagram_id": diagram_id},
    )
    return {"id": diagram_id}


@router.delete("/{diagram_id}", status_code=204)
async def delete_diagram(
    diagram_id: str,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
):
    """Delete a diagram (ownership-checked). Returns 204 on success."""
    session_id: str = request.state.session_id
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    repo.delete_diagram(diagram_id)
    logger.info(
        "Diagram deleted",
        extra={"correlation_id": session_id, "diagram_id": diagram_id},
    )
    return Response(status_code=204)
