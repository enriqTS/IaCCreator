"""EC2-specific configuration model."""

from typing import ClassVar, Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class Ec2Config(BaseServiceConfig):
    """EC2-specific configuration — single source of truth."""

    service_type: Literal[ServiceType.EC2] = ServiceType.EC2

    _schema_field_order: ClassVar[tuple[str, ...]] = (
        "instance_name",
        "ami",
        "instance_type",
    )

    # ── General ───────────────────────────────────────────────────────────
    instance_name: str | None = TerraformField(
        None,
        group="General",
        description="Name tag for the EC2 instance",
    )
    ami: str | None = TerraformField(
        None,
        group="General",
        description="AMI ID for the instance",
    )
    instance_type: str | None = TerraformField(
        "t3.micro",
        group="General",
        description="EC2 instance type",
    )

    # ── Internal (not Terraform variables) ────────────────────────────────
    key_name: str | None = None
