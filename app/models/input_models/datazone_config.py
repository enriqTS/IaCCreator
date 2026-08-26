"""Amazon DataZone domain configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class DataZoneConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.DATAZONE] = ServiceType.DATAZONE
    domain_name: str = TerraformField("data-domain", description="DataZone domain name")
    domain_execution_role: str = TerraformField(
        "", description="DataZone domain execution role ARN"
    )
    description: str | None = TerraformField(None, description="Domain description")
    kms_key_identifier: str | None = TerraformField(
        None, description="KMS key ARN or ID"
    )
