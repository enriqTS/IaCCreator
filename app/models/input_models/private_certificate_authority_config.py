from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class PrivateCertificateAuthorityConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.PRIVATE_CERTIFICATE_AUTHORITY] = (
        ServiceType.PRIVATE_CERTIFICATE_AUTHORITY
    )
    common_name: str = TerraformField(
        "Example Root CA", description="Certificate authority common name"
    )
    organization: str = TerraformField(
        "Example Organization", description="Certificate authority organization"
    )
    key_algorithm: str = TerraformField(
        "RSA_2048", description="Certificate authority key algorithm"
    )
    signing_algorithm: str = TerraformField(
        "SHA256WITHRSA", description="Certificate signing algorithm"
    )
    usage_mode: str = TerraformField(
        "GENERAL_PURPOSE", description="Certificate authority usage mode"
    )
    permanent_deletion_time_in_days: int = TerraformField(
        30, description="CA restoration period after deletion"
    )
