from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class VerifiedPermissionsConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.VERIFIED_PERMISSIONS] = (
        ServiceType.VERIFIED_PERMISSIONS
    )
    description: str = TerraformField(
        "Application authorization policies", description="Policy store description"
    )
    validation_mode: str = TerraformField(
        "STRICT", description="Cedar policy validation mode"
    )
