from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class VpcLatticeConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.VPC_LATTICE] = ServiceType.VPC_LATTICE
    service_network_name: str = TerraformField(
        "service-network", description="VPC Lattice service network name"
    )
    auth_type: str = TerraformField(
        "AWS_IAM", description="Service network authentication type"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Service network tags"
    )
