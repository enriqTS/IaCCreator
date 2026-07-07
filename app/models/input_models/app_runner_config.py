"""App Runner-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AppRunnerConfig(BaseServiceConfig):
    """App Runner-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.APP_RUNNER] = ServiceType.APP_RUNNER

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "service_name",
        "image_identifier",
    )

    # ── General ───────────────────────────────────────────────────────────
    service_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the App Runner service",
    )
    image_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Container image identifier for the App Runner service",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    apprunner_source_type: str | None = None
