"""DocumentDB-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class DocumentDbConfig(BaseServiceConfig):
    """DocumentDB-specific configuration."""

    service_type: Literal[ServiceType.DOCUMENTDB] = ServiceType.DOCUMENTDB

    _iam_client_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
        "master_username",
        "engine_version",
    )

    engine_version: str | None = TerraformField(
        None,
        description="DocumentDB engine version; IAM client connections require explicit version 5.0",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the DocumentDB cluster",
    )
    master_username: str | None = TerraformField(
        None,
        group="General",
        description="Master username for the DocumentDB cluster",
    )
