"""AWS Secrets Manager secret configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, ValidationRule


class SecretsManagerConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SECRETS_MANAGER] = ServiceType.SECRETS_MANAGER
    description: str | None = TerraformField(None, description="Secret description")
    kms_key_id: str | None = TerraformField(None, description="KMS key ARN or ID")
    recovery_window_in_days: int = TerraformField(
        30,
        description="Days before permanent deletion",
        validation=ValidationRule(min=0, max=30),
    )
