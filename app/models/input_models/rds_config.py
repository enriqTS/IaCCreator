"""RDS-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class RdsConfig(BaseServiceConfig):
    """RDS-specific configuration."""

    service_type: Literal[ServiceType.RDS] = ServiceType.RDS

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "db_identifier",
        "engine",
        "instance_class",
        "allocated_storage",
        "username",
    )

    # ── General ───────────────────────────────────────────────────────────
    db_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the RDS instance",
    )
    engine: str | None = TerraformField(
        None,
        group="General",
        description="Database engine type",
    )
    instance_class: str | None = TerraformField(
        "db.t3.micro",
        group="General",
        description="RDS instance class",
    )
    allocated_storage: int | None = TerraformField(
        20,
        group="General",
        description="Allocated storage in GB",
    )
    username: str | None = TerraformField(
        None,
        group="General",
        description="Master username for the database",
    )
