"""Subnet configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class SubnetConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SUBNET] = ServiceType.SUBNET
    vpc_id: str = TerraformField("", description="VPC ID")
    cidr_block: str = TerraformField(
        "10.0.1.0/24",
        description="IPv4 CIDR block",
        validation=ValidationRule(pattern=r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$"),
    )
    availability_zone: str | None = TerraformField(
        None, description="Availability Zone"
    )
    map_public_ip_on_launch: bool = TerraformField(
        False, description="Assign public IPv4 addresses"
    )
