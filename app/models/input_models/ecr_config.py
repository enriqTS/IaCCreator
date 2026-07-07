"""ECR-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class EcrConfig(BaseServiceConfig):
    """ECR-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.ECR] = ServiceType.ECR

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "repository_name",
    )

    # ── General ───────────────────────────────────────────────────────────
    repository_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the ECR repository",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    ecr_image_tag_mutability: str | None = None
    ecr_scan_on_push: bool | None = None
