"""Neptune-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class NeptuneConfig(BaseServiceConfig):
    """Neptune-specific configuration."""

    service_type: Literal[ServiceType.NEPTUNE] = ServiceType.NEPTUNE

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the Neptune cluster",
    )
