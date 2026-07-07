"""SES-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class SesConfig(BaseServiceConfig):
    """SES-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.SES] = ServiceType.SES

    _schema_field_order: ClassVar[tuple[str, ...]] = ("domain",)

    # ── General ───────────────────────────────────────────────────────────
    domain: str | None = TerraformField(
        None,
        group="General",
        description="Domain name for SES identity",
    )
