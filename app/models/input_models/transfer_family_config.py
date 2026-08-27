from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class TransferFamilyConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.TRANSFER_FAMILY] = ServiceType.TRANSFER_FAMILY
    protocols: list[str] = TerraformField(
        default_factory=lambda: ["SFTP"], description="Enabled transfer protocols"
    )
    endpoint_type: str = TerraformField(
        "PUBLIC",
        description="Server endpoint type",
        options=[
            OptionEntry(value="PUBLIC", label="Public"),
            OptionEntry(value="VPC", label="VPC hosted"),
        ],
    )
    identity_provider_type: str = TerraformField(
        "SERVICE_MANAGED",
        description="Identity provider type",
        options=[
            OptionEntry(value="SERVICE_MANAGED", label="Service managed"),
            OptionEntry(value="AWS_DIRECTORY_SERVICE", label="Directory Service"),
            OptionEntry(value="API_GATEWAY", label="API Gateway"),
            OptionEntry(value="AWS_LAMBDA", label="Lambda"),
        ],
    )
    force_destroy: bool = TerraformField(
        False, description="Delete the server even when users exist"
    )
    tags: dict[str, str] = TerraformField(
        default_factory=dict, description="Server tags"
    )
