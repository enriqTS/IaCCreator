"""VPC configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
)


class VpcConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.VPC] = ServiceType.VPC
    cidr_block: str = TerraformField(
        "10.0.0.0/16",
        description="IPv4 CIDR block",
        validation=ValidationRule(pattern=r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$"),
    )
    instance_tenancy: str = TerraformField(
        "default",
        description="Instance tenancy",
        options=[
            OptionEntry(value="default", label="Default"),
            OptionEntry(value="dedicated", label="Dedicated"),
        ],
    )
    enable_dns_support: bool = TerraformField(True, description="Enable DNS resolution")
    enable_dns_hostnames: bool = TerraformField(
        True, description="Enable DNS hostnames"
    )
