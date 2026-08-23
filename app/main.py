"""FastAPI application — Terraform IaC Generator endpoints."""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.exception_handlers import domain_error_handler
from app.exceptions import DomainError
from app.generators.schema_validator import validate_config_against_schema
from app.logging_config import configure_logging
from app.middleware.session_middleware import SessionMiddleware
from app.models.connection_configs.schema_models import (
    ConnectionSchemaEntry,
    ConnectionSchemasResponse,
)
from app.models.connection_previews import ConnectionPreviewResponse
from app.models.input_models import ArchitectureDescription
from app.models.input_models._general import _get_cached_service_config_models
from app.models.input_models._naming import (
    RESOURCE_NAME_DESCRIPTION,
    RESOURCE_NAME_MAX_LENGTH,
    RESOURCE_NAME_PATTERN,
)
from app.models.ir_models import GenerationSummary
from app.models.response_models import (
    GenerationResponse,
    NamingRulesResponse,
    VariableSchemasResponse,
)
from app.persistence.factory import get_repository
from app.routers.diagrams import router as diagram_router
from app.services.code_generator import CodeGenerator
from app.services.connection_handlers.registry import CONNECTION_SPECS
from app.services.connection_previewer import ConnectionPreviewer
from app.services.ir_builder import IRBuilder
from app.services.openapi.mapper import map_openapi
from app.services.openapi.models import (
    OpenApiImportRequest,
    OpenApiImportResponse,
)
from app.services.openapi.parser import parse_openapi
from app.services.output_serializer import OutputSerializer
from app.services.session_manager import SessionManager

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Terraform IaC Generator",
    description="Generates modular Terraform file structures from architecture descriptions",
    version="0.1.0",
)

logger.info(
    "Application started",
    extra={
        "correlation_id": "startup",
        "app_name": "Terraform IaC Generator",
        "version": "0.1.0",
        "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
    },
)

# --- CORS middleware (must be added BEFORE session middleware) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# --- Session middleware ---
_repository = get_repository()
_session_manager = SessionManager(_repository)
app.add_middleware(SessionMiddleware, session_manager=_session_manager)

# --- Exception handlers ---
app.add_exception_handler(DomainError, domain_error_handler)

# --- Diagram router ---
app.include_router(diagram_router)

_ir_builder = IRBuilder()
_code_gen = CodeGenerator()
_serializer = OutputSerializer()
_previewer = ConnectionPreviewer()


def _build_summary(arch: ArchitectureDescription, file_tree: dict) -> GenerationSummary:
    """Derive a GenerationSummary from the input and generated file tree."""
    from app.models.input_models import ServiceType

    {r.name for r in arch.resources if r.service_type == ServiceType.LAMBDA}
    iam_policy_count = sum(
        1 for p in file_tree if p.endswith("-policy.json") and "/iam-policies/" in p
    )
    return GenerationSummary(
        project_name=arch.project_name,
        environment_count=len(arch.environments),
        module_count=len({r.service_type for r in arch.resources}),
        resource_instance_count=len(arch.resources),
        iam_policy_count=iam_policy_count,
    )


@app.post("/generate/zip")
async def generate_zip(arch: ArchitectureDescription) -> Response:
    """Generate Terraform files and return them as a ZIP archive."""
    try:
        for resource in arch.resources:
            validate_config_against_schema(resource.service_type, resource.config)
        project_ir = _ir_builder.build(arch)
        file_tree = _code_gen.generate(project_ir)
        zip_bytes = _serializer.to_zip(file_tree, strip_prefix=arch.project_name)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{arch.project_name}.zip"'
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Generation failed",
            exc_info=True,
            extra={"correlation_id": "anonymous"},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        ) from exc


@app.post("/generate/json", response_model=GenerationResponse)
async def generate_json(arch: ArchitectureDescription) -> GenerationResponse:
    """Generate Terraform files and return them as JSON with a summary."""
    try:
        for resource in arch.resources:
            validate_config_against_schema(resource.service_type, resource.config)
        project_ir = _ir_builder.build(arch)
        file_tree = _code_gen.generate(project_ir)
        summary = _build_summary(arch, file_tree)
        return GenerationResponse(files=file_tree, summary=summary)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Generation failed",
            exc_info=True,
            extra={"correlation_id": "anonymous"},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        ) from exc


@app.post("/api/import/openapi", response_model=OpenApiImportResponse)
async def import_openapi(request: OpenApiImportRequest) -> OpenApiImportResponse:
    """Turn an OpenAPI document into API Gateway routes, authorizers and settings."""
    document = parse_openapi(request.content)
    return map_openapi(document, request.selected_server_url)


@app.get("/api/naming-rules", response_model=NamingRulesResponse)
async def get_naming_rules() -> NamingRulesResponse:
    """Return the rules the backend enforces on resource names."""
    return NamingRulesResponse(
        pattern=RESOURCE_NAME_PATTERN,
        description=RESOURCE_NAME_DESCRIPTION,
        max_length=RESOURCE_NAME_MAX_LENGTH,
    )


@app.get("/api/connection-schemas", response_model=ConnectionSchemasResponse)
async def get_connection_schemas() -> ConnectionSchemasResponse:
    """Return every connection kind with the fields the editor should render."""
    return ConnectionSchemasResponse(
        connections=[
            ConnectionSchemaEntry(
                source=spec.source.value,
                target=spec.target.value,
                connection_type=spec.connection_type,
                label=spec.label,
                is_default=spec.is_default,
                fields=spec.config_model.get_field_schema(),
            )
            for spec in CONNECTION_SPECS
        ]
    )


@app.post("/api/connections/preview", response_model=ConnectionPreviewResponse)
async def preview_connections(
    arch: ArchitectureDescription,
) -> ConnectionPreviewResponse:
    """Describe what every connection contributes, and what is wrong with it."""
    project = _ir_builder.build(arch)
    return ConnectionPreviewResponse(previews=_previewer.preview_all(project))


@app.get("/api/variable-schemas", response_model=VariableSchemasResponse)
async def get_variable_schemas() -> VariableSchemasResponse:
    """Return all variable schemas using model introspection.

    All services are now migrated to TerraformField annotations, so schemas
    are derived exclusively from per-service config models.
    """
    # Introspection failures are bugs, so they surface rather than dropping a service
    return VariableSchemasResponse(
        {
            stype.value: config_cls.get_variable_schema()
            for stype, config_cls in _get_cached_service_config_models().items()
            if config_cls.has_terraform_schema()
        }
    )
