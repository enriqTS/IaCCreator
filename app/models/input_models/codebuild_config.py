"""CodeBuild-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

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
        "image",
        "compute_type",
        "buildspec",
    )

    _inject_runtime_secrets: bool = PrivateAttr(default=False)

    image: str = TerraformField(
        "aws/codebuild/standard:7.0",
        group="Environment",
        description="Build container image",
    )
    compute_type: str = TerraformField(
        "BUILD_GENERAL1_SMALL", group="Environment", description="Build compute type"
    )
    buildspec: str = TerraformField(
        "version: 0.2\nphases:\n  build:\n    commands:\n      - echo Configure your build commands\n",
        group="Source",
        description="Inline buildspec or source-relative buildspec path",
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
        "NO_SOURCE",
        group="General",
        description="Source type for the CodeBuild project",
    )
