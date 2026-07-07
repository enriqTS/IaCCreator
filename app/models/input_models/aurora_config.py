"""Aurora-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AuroraConfig(BaseServiceConfig):
    """Aurora-specific configuration."""

    service_type: Literal[ServiceType.AURORA] = ServiceType.AURORA

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
        "engine",
        "master_username",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the Aurora cluster",
    )
    engine: str | None = TerraformField(
        None,
        group="General",
        description="Database engine for the Aurora cluster",
    )
    master_username: str | None = TerraformField(
        None,
        group="General",
        description="Master username for the Aurora cluster",
    )
