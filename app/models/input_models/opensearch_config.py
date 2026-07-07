"""OpenSearch-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class OpenSearchConfig(BaseServiceConfig):
    """OpenSearch-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.OPENSEARCH] = ServiceType.OPENSEARCH

    # Field order must match VARIABLE_SCHEMAS[ServiceType.OPENSEARCH] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = ("domain_name",)

    # ── General ───────────────────────────────────────────────────────────
    domain_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the OpenSearch domain",
    )
