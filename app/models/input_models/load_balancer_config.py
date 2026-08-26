"""Elastic load balancer configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField, VisibleWhen


class LoadBalancerConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.LOAD_BALANCER] = ServiceType.LOAD_BALANCER
    load_balancer_name: str = TerraformField(
        "load-balancer", description="Load balancer name"
    )
    load_balancer_type: str = TerraformField(
        "application",
        description="Load balancer type",
        options=[
            OptionEntry(value="application", label="Application"),
            OptionEntry(value="network", label="Network"),
            OptionEntry(value="gateway", label="Gateway"),
        ],
    )
    internal: bool = TerraformField(False, description="Use an internal scheme")
    subnet_ids: str = TerraformField("", description="Comma-separated subnet IDs")
    security_group_ids: str = TerraformField(
        "",
        description="Comma-separated security group IDs",
        visible_when=VisibleWhen(field="load_balancer_type", equals="application"),
    )
    enable_deletion_protection: bool = TerraformField(
        False, description="Enable deletion protection"
    )
