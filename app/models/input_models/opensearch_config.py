"""OpenSearch-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class OpenSearchConfig(BaseServiceConfig):
    """OpenSearch-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.OPENSEARCH] = ServiceType.OPENSEARCH
    _index_client_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = ("domain_name",)

    # ── General ───────────────────────────────────────────────────────────
    domain_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the OpenSearch domain",
    )
