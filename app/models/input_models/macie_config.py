from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class MacieConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MACIE] = ServiceType.MACIE
    status: str = TerraformField("ENABLED", description="Macie account status")
    finding_publishing_frequency: str = TerraformField(
        "FIFTEEN_MINUTES", description="Finding publishing frequency"
    )
