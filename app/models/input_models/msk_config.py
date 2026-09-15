"""MSK-specific configuration model."""

from typing import ClassVar, Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField

MSK_IAM_VERSION_PATTERN = (
    r"^(([3-9]|[1-9][0-9]+)\.|2\.([89]|[1-9][0-9]+)\.|2\.7\.[1-9][0-9]*($|\.))"
)


class MskConfig(BaseServiceConfig):
    """MSK-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.MSK] = ServiceType.MSK

    _iam_client_access: bool = PrivateAttr(default=False)

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "cluster_name",
        "kafka_version",
        "number_of_broker_nodes",
        "broker_instance_type",
        "subnet_ids",
        "security_group_ids",
    )

    broker_instance_type: str = TerraformField(
        "kafka.m5.large",
        description="MSK broker instance type",
    )
    subnet_ids: list[str] = TerraformField(
        [], description="Broker subnets in distinct availability zones"
    )
    security_group_ids: list[str] = TerraformField(
        [], description="Broker security groups"
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
