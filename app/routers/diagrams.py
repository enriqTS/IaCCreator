"""Diagram CRUD endpoints scoped to the caller's session."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.models.diagram_models import DiagramIdResponse, DiagramStateInput
from app.models.diagram_state import DiagramState
from app.persistence.base import AbstractRepository
from app.persistence.factory import get_repository
from app.persistence.models import DiagramRecord, DiagramSummary
from app.services.diagram_normalizer import DiagramNormalizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagrams")
_normalizer = DiagramNormalizer()


def get_repo() -> AbstractRepository:
    """Return the overridable repository dependency."""
    return get_repository()


async def verify_ownership(
    diagram_id: str,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
) -> DiagramRecord:
    """Fetch a diagram and enforce session ownership."""
    record = repo.get_diagram(diagram_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    if record.session_id != request.state.session_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return record


@router.post("", response_model=DiagramIdResponse)
async def create_diagram(
    body: DiagramStateInput,
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
) -> DiagramIdResponse:
    """Create a canonical diagram for the current session."""
    canonical = _normalizer.normalize(body.model_dump())
    diagram_id = repo.save_diagram(request.state.session_id, canonical.model_dump())
    logger.info("Diagram created", extra={"diagram_id": diagram_id})
    return DiagramIdResponse(id=diagram_id)


@router.get("", response_model=list[DiagramSummary])
async def list_diagrams(
    request: Request,
    repo: AbstractRepository = Depends(get_repo),
) -> list[DiagramSummary]:
    """Return diagrams belonging to the current session."""
    return repo.list_diagrams(request.state.session_id)


@router.get("/{diagram_id}", response_model=DiagramState)
async def get_diagram(
    diagram_id: str,
    request: Request,
    record: DiagramRecord = Depends(verify_ownership),
) -> DiagramState:
    """Load a canonical diagram."""
    return _normalizer.normalize(record.diagram_state)


@router.put("/{diagram_id}", response_model=DiagramIdResponse)
async def update_diagram(
    diagram_id: str,
    body: DiagramStateInput,
    request: Request,
    record: DiagramRecord = Depends(verify_ownership),
    repo: AbstractRepository = Depends(get_repo),
) -> DiagramIdResponse:
    """Update an owned diagram with canonical state."""
    canonical = _normalizer.normalize(body.model_dump())
    repo.update_diagram(diagram_id, canonical.model_dump())
    return DiagramIdResponse(id=diagram_id)


@router.delete("/{diagram_id}", status_code=204)
async def delete_diagram(
    diagram_id: str,
    request: Request,
    record: DiagramRecord = Depends(verify_ownership),
    repo: AbstractRepository = Depends(get_repo),
) -> Response:
    """Delete an owned diagram."""
    repo.delete_diagram(diagram_id)
    return Response(status_code=204)
