"""Lightsail-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class LightsailConfig(BaseServiceConfig):
    """Lightsail-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.LIGHTSAIL] = ServiceType.LIGHTSAIL

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "instance_name",
        "blueprint_id",
        "bundle_id",
        "availability_zone",
    )

    # ── General ───────────────────────────────────────────────────────────
    instance_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Lightsail instance",
    )
    blueprint_id: str | None = TerraformField(
        None,
        group="General",
        description="Blueprint ID for the Lightsail instance",
    )
    bundle_id: str | None = TerraformField(
        None,
        group="General",
        description="Bundle ID for the Lightsail instance",
    )
    availability_zone: str | None = TerraformField(
        None,
        group="General",
        description="Availability zone for the Lightsail instance",
    )
