"""AWS Lake Formation resource registration configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField, VisibleWhen


class LakeFormationConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.LAKE_FORMATION] = ServiceType.LAKE_FORMATION
    resource_arn: str = TerraformField(
        "", description="S3 resource ARN registered with Lake Formation"
    )
    use_service_linked_role: bool = TerraformField(
        True, description="Use the Lake Formation service-linked role"
    )
    role_arn: str | None = TerraformField(
        None,
        description="IAM role used to access the resource",
        visible_when=VisibleWhen(field="use_service_linked_role", equals=False),
    )
    hybrid_access_enabled: bool = TerraformField(
        False, description="Enable hybrid IAM and Lake Formation permissions"
    )
    with_federation: bool = TerraformField(
        False, description="Enable access through a federated catalog"
    )
