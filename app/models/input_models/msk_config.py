"""MSK-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class MskConfig(BaseServiceConfig):
    """MSK-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.MSK] = ServiceType.MSK

    # Field order must match VARIABLE_SCHEMAS[ServiceType.MSK] exactly.
    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "kafka_version",
        "number_of_broker_nodes",
    )

    # ── General ───────────────────────────────────────────────────────────
    cluster_name: str | None = TerraformField(
        None,
        group="General",
        description="Name of the MSK cluster",
    )
    kafka_version: str | None = TerraformField(
        None,
        group="General",
        description="Apache Kafka version for the MSK cluster",
    )
    number_of_broker_nodes: int | None = TerraformField(
        None,
        group="General",
        description="Number of broker nodes in the MSK cluster",
    )
