"""AppStream-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AppStreamConfig(BaseServiceConfig):
    """AppStream-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.APPSTREAM] = ServiceType.APPSTREAM

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "fleet_name",
        "instance_type",
    )

    # ── General ───────────────────────────────────────────────────────────
    fleet_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the AppStream fleet",
    )
    instance_type: str | None = TerraformField(
        None,
        group="General",
        description="Instance type for the AppStream fleet",
    )
