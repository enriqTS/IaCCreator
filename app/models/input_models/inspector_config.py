from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class InspectorConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.INSPECTOR] = ServiceType.INSPECTOR
    account_ids: list[str] = TerraformField(
        default_factory=list, description="AWS account IDs to enable"
    )
    resource_types: list[str] = TerraformField(
        default_factory=lambda: ["EC2", "ECR", "LAMBDA"],
        description="Inspector scan resource types",
    )
