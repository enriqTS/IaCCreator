"""Batch-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class BatchConfig(BaseServiceConfig):
    """Batch-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BATCH] = ServiceType.BATCH

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "compute_environment_name",
        "service_role_arn",
    )

    # ── General ───────────────────────────────────────────────────────────
    compute_environment_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Batch compute environment",
    )
    service_role_arn: str | None = TerraformField(
        None,
        group="General",
        description="ARN of the IAM service role for Batch",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    batch_compute_environment_type: str | None = None
    batch_max_vcpus: int | None = None
