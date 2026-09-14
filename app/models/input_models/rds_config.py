"""RDS-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class RdsConfig(BaseServiceConfig):
    """RDS-specific configuration."""

    service_type: Literal[ServiceType.RDS] = ServiceType.RDS

    _iam_database_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "manage_master_user_password",
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

    manage_master_user_password: bool = TerraformField(
        False,
        description="Explicitly allow RDS to create and manage the master password in Secrets Manager",
    )
