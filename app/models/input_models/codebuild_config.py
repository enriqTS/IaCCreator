"""CodeBuild-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CodeBuildConfig(BaseServiceConfig):
    """CodeBuild-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CODEBUILD] = ServiceType.CODEBUILD

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "project_name",
        "service_role",
        "source_type",
    )

    # ── General ───────────────────────────────────────────────────────────
    project_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CodeBuild project",
    )
    service_role: str | None = TerraformField(
        None,
        group="General",
        description="IAM service role ARN for CodeBuild",
    )
    source_type: str | None = TerraformField(
        None,
        group="General",
        description="Source type for the CodeBuild project",
    )
