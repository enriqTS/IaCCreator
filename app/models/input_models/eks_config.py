"""EKS-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class EksConfig(BaseServiceConfig):
    """EKS-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.EKS] = ServiceType.EKS

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "cluster_role_arn",
        "subnet_ids",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the EKS cluster",
    )
    cluster_role_arn: str | None = TerraformField(
        None,
        group="General",
        description="ARN of the IAM role for the EKS cluster",
    )

    # ── Networking ────────────────────────────────────────────────────────
    subnet_ids: list[str] | None = TerraformField(
        None,
        group="Networking",
        description="List of subnet IDs for the EKS cluster VPC config",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    eks_version: str | None = None
    eks_endpoint_public_access: bool | None = None
