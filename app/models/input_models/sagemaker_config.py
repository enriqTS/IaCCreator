"""SageMaker-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class SageMakerConfig(BaseServiceConfig):
    """SageMaker-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.SAGEMAKER] = ServiceType.SAGEMAKER

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "notebook_instance_name",
        "instance_type",
        "role_arn",
        "volume_size",
        "direct_internet_access",
        "root_access",
        "tags",
    )

    # ── General ───────────────────────────────────────────────────────────
    notebook_instance_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the SageMaker notebook instance",
    )
    instance_type: str | None = TerraformField(
        None,
        group="General",
        description="Instance type for the notebook instance",
        options=[
            OptionEntry(value="ml.t3.medium", label="ml.t3.medium"),
            OptionEntry(value="ml.t3.large", label="ml.t3.large"),
            OptionEntry(value="ml.m5.large", label="ml.m5.large"),
            OptionEntry(value="ml.m5.xlarge", label="ml.m5.xlarge"),
            OptionEntry(value="ml.c5.large", label="ml.c5.large"),
            OptionEntry(value="ml.c5.xlarge", label="ml.c5.xlarge"),
        ],
    )
    role_arn: str | None = TerraformField(
        None,
        group="General",
        description="IAM role ARN for the notebook instance",
    )

    # ── Configuration ─────────────────────────────────────────────────────
    volume_size: int | None = TerraformField(
        5,
        group="Configuration",
        description="Volume size for the notebook instance in GB",
        validation=ValidationRule(min=5, max=16384),
    )
    direct_internet_access: bool | None = TerraformField(
        True,
        group="Configuration",
        description="Whether direct internet access is enabled for the notebook instance",
    )
    root_access: bool | None = TerraformField(
        True,
        group="Configuration",
        description="Whether root access is enabled for the notebook instance",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    tags: dict[str, str] | None = TerraformField(
        None,
        group="Metadata",
        description="Tags to apply to the SageMaker notebook instance",
    )
