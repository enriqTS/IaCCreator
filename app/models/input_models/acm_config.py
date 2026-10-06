"""AWS Certificate Manager certificate configuration model."""

from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField
from app.models.private_certificate import PrivateCertificateBinding


class AcmConfig(BaseServiceConfig):
    _private_ca: PrivateCertificateBinding | None = PrivateAttr(default=None)
    service_type: Literal[ServiceType.CERTIFICATE_MANAGER] = (
        ServiceType.CERTIFICATE_MANAGER
    )
    domain_name: str = TerraformField(
        "example.com", description="Primary certificate domain"
    )
    subject_alternative_names: list[str] = TerraformField(
        [], description="Additional certificate domains"
    )
    validation_method: str = TerraformField(
        "DNS",
        description="Certificate validation method",
        options=[
            OptionEntry(value="DNS", label="DNS"),
            OptionEntry(value="EMAIL", label="Email"),
        ],
    )
