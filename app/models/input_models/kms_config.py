"""AWS KMS key configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class KmsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.KMS] = ServiceType.KMS
    description: str = TerraformField(
        "Managed by IaCCreator", description="Key description"
    )
    deletion_window_in_days: int = TerraformField(
        30,
        description="Waiting period before key deletion",
        validation=ValidationRule(min=7, max=30),
    )
    enable_key_rotation: bool = TerraformField(
        True, description="Enable annual key rotation"
    )
    alias: str | None = TerraformField(
        None, description="Optional alias without the alias/ prefix"
    )
    multi_region: bool = TerraformField(
        False, description="Create a multi-Region primary key"
    )
