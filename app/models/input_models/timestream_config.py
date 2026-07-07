"""Timestream-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class TimestreamConfig(BaseServiceConfig):
    """Timestream-specific configuration."""

    service_type: Literal[ServiceType.TIMESTREAM] = ServiceType.TIMESTREAM

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "database_name",
    )

    # ── General ───────────────────────────────────────────────────────────
    database_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the Timestream database",
    )
