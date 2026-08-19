"""Typed response models so the generated OpenAPI document describes real payloads."""

from __future__ import annotations

from pydantic import BaseModel, RootModel

from app.models.input_models._metadata import VariableSchemaEntry
from app.models.ir_models import GenerationSummary


class VariableSchemasResponse(RootModel[dict[str, list[VariableSchemaEntry]]]):
    """Variable schemas keyed by service type."""


class NamingRulesResponse(BaseModel):
    """The rules a resource name must satisfy, so clients can check before submitting."""

    pattern: str
    description: str
    max_length: int


class GenerationResponse(BaseModel):
    """Generated Terraform files plus a summary of the run."""

    files: dict[str, str]
    summary: GenerationSummary
