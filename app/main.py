"""FastAPI application — Terraform IaC Generator endpoints."""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.exception_handlers import domain_error_handler
from app.exceptions import DomainError
from app.generators.schema_validator import validate_config_against_schema
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.logging_config import configure_logging
from app.middleware.session_middleware import SessionMiddleware
from app.models.input_models import ArchitectureDescription
from app.models.input_models._general import _get_cached_service_config_models
from app.models.ir_models import GenerationSummary
from app.persistence.factory import get_repository
from app.routers.diagrams import router as diagram_router
from app.services.code_generator import CodeGenerator
from app.services.ir_builder import IRBuilder
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


def _build_summary(arch: ArchitectureDescription, file_tree: dict) -> GenerationSummary:
    """Derive a GenerationSummary from the input and generated file tree."""
    from app.models.input_models import ServiceType

    lambda_names = {
        r.name for r in arch.resources if r.service_type == ServiceType.LAMBDA
    }
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
        )


@app.post("/generate/json")
async def generate_json(arch: ArchitectureDescription) -> JSONResponse:
    """Generate Terraform files and return them as JSON with a summary."""
    try:
        for resource in arch.resources:
            validate_config_against_schema(resource.service_type, resource.config)
        project_ir = _ir_builder.build(arch)
        file_tree = _code_gen.generate(project_ir)
        summary = _build_summary(arch, file_tree)
        result = _serializer.to_json(file_tree, summary)
        return JSONResponse(content=result)
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
        )


@app.get("/api/variable-schemas")
async def get_variable_schemas() -> dict[str, list[dict]]:
    """Return all variable schemas, using model introspection where available."""
    result: dict[str, list[dict]] = {}
    config_models = _get_cached_service_config_models()

    for stype, entries in VARIABLE_SCHEMAS.items():
        config_cls = config_models.get(stype)

        if config_cls is not None and config_cls.has_terraform_schema():
            try:
                schema = config_cls.get_variable_schema()
                result[stype.value] = [entry.model_dump() for entry in schema]
            except Exception:
                logger.error(
                    f"Introspection failed for {stype.value}, falling back to legacy"
                )
                result[stype.value] = [entry.model_dump() for entry in entries]
        else:
            # Legacy path — service not yet migrated
            result[stype.value] = [entry.model_dump() for entry in entries]

    return result
