"""Amazon EFS file system configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField, VisibleWhen


class EfsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.EFS] = ServiceType.EFS
    encrypted: bool = TerraformField(True, description="Encrypt data at rest")
    kms_key_id: str | None = TerraformField(None, description="KMS key ARN or ID")
    performance_mode: str = TerraformField(
        "generalPurpose",
        description="File system performance mode",
        options=[
            OptionEntry(value="generalPurpose", label="General purpose"),
            OptionEntry(value="maxIO", label="Max I/O"),
        ],
    )
    throughput_mode: str = TerraformField(
        "bursting",
        description="Throughput mode",
        options=[
            OptionEntry(value=value, label=value.title())
            for value in ("bursting", "elastic", "provisioned")
        ],
    )
    provisioned_throughput_in_mibps: float = TerraformField(
        1.0,
        description="Provisioned throughput in MiB/s",
        visible_when=VisibleWhen(field="throughput_mode", equals="provisioned"),
    )
    subnet_ids: list[str] = TerraformField(
        [], description="Subnets where mount targets are created"
    )
    security_group_ids: list[str] = TerraformField(
        [], description="Security groups for mount targets"
    )
