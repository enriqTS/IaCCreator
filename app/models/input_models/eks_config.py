"""EKS-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class EksConfig(BaseServiceConfig):
    """EKS-specific configuration — single source of truth."""

    _control_plane_logs: bool = PrivateAttr(default=False)

    manage_efs_csi_driver: bool = TerraformField(
        True, description="Manage the EFS CSI add-on when EFS mounts are connected"
    )
    efs_csi_addon_version: str | None = TerraformField(
        None, description="Optional compatible EFS CSI add-on version"
    )

    service_type: Literal[ServiceType.EKS] = ServiceType.EKS

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "cluster_role_arn",
        "subnet_ids",
        "security_group_ids",
        "endpoint_private_access",
        "authentication_mode",
        "manage_efs_csi_driver",
        "efs_csi_addon_version",
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
    security_group_ids: list[str] | None = TerraformField(
        None,
        group="Networking",
        description="Additional security group IDs for the EKS control plane",
    )
    endpoint_private_access: bool | None = TerraformField(
        None,
        group="Networking",
        description="Enable private EKS API access; managed Prometheus collection defaults this to true",
    )
    authentication_mode: Literal["CONFIG_MAP", "API", "API_AND_CONFIG_MAP"] | None = (
        TerraformField(
            None,
            description="EKS authentication mode; enabling API access cannot be reversed",
            options=[
                OptionEntry(value=value, label=value)
                for value in ("CONFIG_MAP", "API", "API_AND_CONFIG_MAP")
            ],
        )
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    eks_version: str | None = None
    eks_endpoint_public_access: bool | None = None
