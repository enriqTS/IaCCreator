"""AWS Database Migration Service replication instance configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class DmsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.DATABASE_MIGRATION_SERVICE] = (
        ServiceType.DATABASE_MIGRATION_SERVICE
    )
    replication_instance_id: str = TerraformField(
        "replication-instance", description="Replication instance identifier"
    )
    replication_instance_class: str = TerraformField(
        "dms.t3.medium", description="Replication instance class"
    )
    allocated_storage: int = TerraformField(
        50, description="Allocated storage in GiB", validation=ValidationRule(min=5)
    )
    engine_version: str | None = TerraformField(
        None, description="Optional DMS engine version"
    )
    multi_az: bool = TerraformField(
        False, description="Deploy a standby replica in another Availability Zone"
    )
    publicly_accessible: bool = TerraformField(
        False, description="Assign a public IP address"
    )
    subnet_ids: list[str] = TerraformField(
        [], description="Subnets for the replication subnet group"
    )
    vpc_security_group_ids: list[str] = TerraformField(
        [], description="VPC security groups for the replication instance"
    )
    auto_minor_version_upgrade: bool = TerraformField(
        True, description="Automatically install minor engine upgrades"
    )
