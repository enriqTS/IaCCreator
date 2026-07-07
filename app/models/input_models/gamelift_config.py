"""GameLift-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class GameLiftConfig(BaseServiceConfig):
    """GameLift-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.GAMELIFT] = ServiceType.GAMELIFT

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "fleet_name",
        "ec2_instance_type",
    )

    # ── General ───────────────────────────────────────────────────────────
    fleet_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the GameLift fleet",
    )
    ec2_instance_type: str | None = TerraformField(
        None,
        group="General",
        description="EC2 instance type for the GameLift fleet",
    )
