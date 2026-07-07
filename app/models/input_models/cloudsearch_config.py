"""CloudSearch-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class CloudSearchConfig(BaseServiceConfig):
    """CloudSearch-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.CLOUDSEARCH] = ServiceType.CLOUDSEARCH

    # Field order must match VARIABLE_SCHEMAS[ServiceType.CLOUDSEARCH] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = ("domain_name",)

    # ── General ───────────────────────────────────────────────────────────
    domain_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the CloudSearch domain",
    )
