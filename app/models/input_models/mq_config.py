"""Amazon MQ broker configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class MqConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MQ] = ServiceType.MQ
    engine_version: str = TerraformField("5.18", description="ActiveMQ engine version")
    host_instance_type: str = TerraformField(
        "mq.t3.micro", description="Broker instance type"
    )
    deployment_mode: str = TerraformField(
        "SINGLE_INSTANCE",
        description="Broker deployment mode",
        options=[
            OptionEntry(value="SINGLE_INSTANCE", label="Single instance"),
            OptionEntry(
                value="ACTIVE_STANDBY_MULTI_AZ", label="Active/standby multi-AZ"
            ),
        ],
    )
    subnet_ids: list[str] = TerraformField([], description="Broker subnet IDs")
    security_group_ids: list[str] = TerraformField(
        [], description="Broker security group IDs"
    )
    publicly_accessible: bool = TerraformField(
        False, description="Allow public broker access"
    )
    username: str = TerraformField("admin", description="Initial broker username")
    password: str = TerraformField("", description="Initial broker password")
    auto_minor_version_upgrade: bool = TerraformField(
        True, description="Automatically install minor engine upgrades"
    )
