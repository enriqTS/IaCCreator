"""Amazon EBS volume configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import (
    OptionEntry,
    TerraformField,
    ValidationRule,
    VisibleWhen,
)


class EbsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.EBS] = ServiceType.EBS
    availability_zone: str = TerraformField(
        "us-east-1a", description="Availability Zone for the volume"
    )
    size: int = TerraformField(
        20, description="Volume size in GiB", validation=ValidationRule(min=1)
    )
    volume_type: str = TerraformField(
        "gp3",
        description="EBS volume type",
        options=[
            OptionEntry(value=value, label=value)
            for value in ("gp3", "gp2", "io1", "io2", "st1", "sc1", "standard")
        ],
    )
    iops: int = TerraformField(
        3000,
        description="Provisioned IOPS",
        validation=ValidationRule(min=100),
        visible_when=VisibleWhen(field="volume_type", equals="gp3"),
    )
    throughput: int = TerraformField(
        125,
        description="Throughput in MiB/s",
        validation=ValidationRule(min=125, max=1000),
        visible_when=VisibleWhen(field="volume_type", equals="gp3"),
    )
    encrypted: bool = TerraformField(True, description="Encrypt the volume")
    kms_key_id: str | None = TerraformField(None, description="KMS key ARN or ID")
    snapshot_id: str | None = TerraformField(None, description="Source snapshot ID")
