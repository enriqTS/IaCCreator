"""CodePipeline-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr, field_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField
from app.models.input_models.codepipeline_stages import normalize_stages


class CodePipelineConfig(BaseServiceConfig):
    """CodePipeline-specific configuration — single source of truth."""

    _managed_artifacts: bool = PrivateAttr(default=False)
    artifact_bucket_name: str | None = TerraformField(
        None, description="External S3 artifact bucket name"
    )
    artifact_kms_key_arn: str | None = TerraformField(
        None, description="Artifact encryption KMS key ARN"
    )
    stages_json: str = TerraformField(
        "[]", description="JSON array of pipeline stages and typed action definitions"
    )

    @field_validator("stages_json")
    @classmethod
    def validate_stages(cls, value: str) -> str:
        return normalize_stages(value)

    service_type: Literal[ServiceType.CODEPIPELINE] = ServiceType.CODEPIPELINE

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "pipeline_name",
        "role_arn",
        "artifact_bucket_name",
        "artifact_kms_key_arn",
        "stages_json",
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
