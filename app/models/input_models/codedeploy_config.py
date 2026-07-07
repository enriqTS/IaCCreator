"""CodeDeploy-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CodeDeployConfig(BaseServiceConfig):
    """CodeDeploy-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CODEDEPLOY] = ServiceType.CODEDEPLOY

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "app_name",
        "compute_platform",
    )

    # ── General ───────────────────────────────────────────────────────────
    app_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CodeDeploy application",
    )
    compute_platform: str | None = TerraformField(
        None,
        group="General",
        description="Compute platform for CodeDeploy",
    )
