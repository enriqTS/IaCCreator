"""EC2 Auto Scaling group configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class Ec2AutoScalingConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.EC2_AUTO_SCALING] = ServiceType.EC2_AUTO_SCALING
    launch_template_id: str = TerraformField("", description="EC2 launch template ID")
    launch_template_version: str = TerraformField(
        "$Latest", description="Launch template version"
    )
    subnet_ids: list[str] = TerraformField(
        [], description="Subnets used by the Auto Scaling group"
    )
    target_group_arns: list[str] = TerraformField(
        [], description="Load balancer target groups attached to the group"
    )
    min_size: int = TerraformField(
        1, description="Minimum instance count", validation=ValidationRule(min=0)
    )
    max_size: int = TerraformField(
        3, description="Maximum instance count", validation=ValidationRule(min=0)
    )
    desired_capacity: int = TerraformField(
        1, description="Desired instance count", validation=ValidationRule(min=0)
    )
    health_check_type: str = TerraformField(
        "EC2",
        description="Health check source",
        options=[
            OptionEntry(value="EC2", label="EC2"),
            OptionEntry(value="ELB", label="Elastic Load Balancing"),
        ],
    )
    health_check_grace_period: int = TerraformField(
        300,
        description="Health check grace period in seconds",
        validation=ValidationRule(min=0),
    )
    termination_policies: list[str] = TerraformField(
        ["Default"], description="Instance termination policies"
    )
