"""Reusable EC2 launch settings, with subnet placement owned by the workload."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class Ec2LaunchTemplateConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.EC2_LAUNCH_TEMPLATE] = (
        ServiceType.EC2_LAUNCH_TEMPLATE
    )
    image_id: str = TerraformField(
        ..., description="AMI ID or resolve:ssm parameter reference"
    )
    instance_type: str = TerraformField("t3.micro", description="EC2 instance type")
    security_group_ids: list[str] = TerraformField(
        [],
        group="Network",
        description="External security group IDs, merged with managed connections",
    )
    key_name: str | None = TerraformField(
        None, description="External EC2 key pair name"
    )
    user_data: str | None = TerraformField(
        None, description="Base64-encoded instance user data"
    )
    iam_instance_profile_name: str | None = TerraformField(
        None, description="External IAM instance profile name"
    )
