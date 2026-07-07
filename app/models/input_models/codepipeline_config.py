"""CodePipeline-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CodePipelineConfig(BaseServiceConfig):
    """CodePipeline-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CODEPIPELINE] = ServiceType.CODEPIPELINE

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "pipeline_name",
        "role_arn",
    )

    # ── General ───────────────────────────────────────────────────────────
    pipeline_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CodePipeline pipeline",
    )
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for CodePipeline",
    )
