"""Batch-specific configuration model."""

import re
from typing import ClassVar, Literal

from pydantic import field_validator

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class BatchConfig(BaseServiceConfig):
    """Batch-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.BATCH] = ServiceType.BATCH

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "compute_environment_name",
        "service_role_arn",
        "batch_compute_environment_type",
        "job_queue_name",
        "job_queue_priority",
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
    job_queue_name: str | None = TerraformField(
        None,
        group="Job Queue",
        description="Name of an optional job queue backed by this compute environment",
        validation=ValidationRule(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    )
    job_queue_priority: int = TerraformField(
        1,
        group="Job Queue",
        description="Priority of the optional job queue",
        validation=ValidationRule(min=0, max=1000),
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    batch_compute_environment_type: str | None = TerraformField(
        None,
        group="General",
        description="Batch compute environment type; unmanaged capacity must be supplied separately",
        options=[
            OptionEntry(value="UNMANAGED", label="Unmanaged"),
            OptionEntry(value="MANAGED", label="Managed"),
        ],
        validation=ValidationRule(allowed_values=["UNMANAGED", "MANAGED"]),
    )
    batch_max_vcpus: int | None = None

    @field_validator("job_queue_name")
    @classmethod
    def validate_job_queue_name(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
            raise ValueError(
                "Job queue name must use 1–128 letters, digits, hyphens, or underscores"
            )
        return value

    @field_validator("job_queue_priority")
    @classmethod
    def validate_job_queue_priority(cls, value: int) -> int:
        if not 0 <= value <= 1000:
            raise ValueError("Job queue priority must be between 0 and 1000")
        return value
