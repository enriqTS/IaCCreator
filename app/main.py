"""FastAPI application — Terraform IaC Generator endpoints."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response

from app.models.input_models import ArchitectureDescription
from app.models.ir_models import GenerationSummary
from app.services.code_generator import CodeGenerator
from app.services.ir_builder import IRBuilder
from app.services.output_serializer import OutputSerializer

app = FastAPI(
    title="Terraform IaC Generator",
    description="Generates modular Terraform file structures from architecture descriptions",
    version="0.1.0",
)

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
        project_ir = _ir_builder.build(arch)
        file_tree = _code_gen.generate(project_ir)
        zip_bytes = _serializer.to_zip(file_tree)
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
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        )


@app.post("/generate/json")
async def generate_json(arch: ArchitectureDescription) -> JSONResponse:
    """Generate Terraform files and return them as JSON with a summary."""
    try:
        project_ir = _ir_builder.build(arch)
        file_tree = _code_gen.generate(project_ir)
        summary = _build_summary(arch, file_tree)
        result = _serializer.to_json(file_tree, summary)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        )
