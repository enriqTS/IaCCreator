"""Amplify-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AmplifyConfig(BaseServiceConfig):
    """Amplify-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.AMPLIFY] = ServiceType.AMPLIFY

    _schema_field_order: ClassVar[tuple[str, ...]] = ("app_name",)

    # ── General ───────────────────────────────────────────────────────────
    app_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Amplify application",
    )
