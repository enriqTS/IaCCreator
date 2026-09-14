"""Aurora-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class AuroraConfig(BaseServiceConfig):
    """Aurora-specific configuration."""

    service_type: Literal[ServiceType.AURORA] = ServiceType.AURORA

    _iam_database_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "manage_master_user_password",
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

    manage_master_user_password: bool = TerraformField(
        False,
        description="Explicitly allow RDS to create and manage the master password in Secrets Manager",
    )
