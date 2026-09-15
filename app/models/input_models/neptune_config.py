"""Neptune-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField

NEPTUNE_DATA_AUTH_VERSION_PATTERN = r"^([2-9][0-9]*|1[0-9]+|1\.([2-9]|[1-9][0-9]+))\."


class NeptuneConfig(BaseServiceConfig):
    """Neptune-specific configuration."""

    service_type: Literal[ServiceType.NEPTUNE] = ServiceType.NEPTUNE

    _iam_graph_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_identifier",
        "engine_version",
    )

    engine_version: str | None = TerraformField(
        None,
        description="Optional Neptune engine version; graph IAM connections require 1.2.0.0 or newer",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_identifier: str | None = TerraformField(
        None,
        group="General",
        description="Identifier for the Neptune cluster",
    )
