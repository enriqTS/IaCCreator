"""Security group configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class SecurityGroupConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SECURITY_GROUP] = ServiceType.SECURITY_GROUP
    vpc_id: str = TerraformField("", description="VPC ID")
    description: str = TerraformField(
        "Managed by Terraform", description="Security group description"
    )
    ingress_protocol: str = TerraformField(
        "tcp",
        group="Ingress",
        description="Ingress protocol",
        options=[
            OptionEntry(value="tcp", label="TCP"),
            OptionEntry(value="udp", label="UDP"),
            OptionEntry(value="-1", label="All"),
        ],
    )
    ingress_from_port: int = TerraformField(
        443,
        group="Ingress",
        description="First ingress port",
        validation=ValidationRule(min=0, max=65535),
    )
    ingress_to_port: int = TerraformField(
        443,
        group="Ingress",
        description="Last ingress port",
        validation=ValidationRule(min=0, max=65535),
    )
    ingress_cidr: str = TerraformField(
        "0.0.0.0/0", group="Ingress", description="Allowed IPv4 CIDR"
    )
    allow_all_egress: bool = TerraformField(
        True, group="Egress", description="Allow all outbound traffic"
    )
