"""Connect-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ConnectConfig(BaseServiceConfig):
    """Connect-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CONNECT] = ServiceType.CONNECT

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "identity_management_type",
        "inbound_calls_enabled",
        "outbound_calls_enabled",
    )

    # ── General ───────────────────────────────────────────────────────────
    identity_management_type: str | None = TerraformField(
        None,
        group="General",
        description="Identity management type for the Connect instance",
    )
    inbound_calls_enabled: bool | None = TerraformField(
        None,
        group="General",
        description="Whether inbound calls are enabled",
    )
    outbound_calls_enabled: bool | None = TerraformField(
        None,
        group="General",
        description="Whether outbound calls are enabled",
    )
