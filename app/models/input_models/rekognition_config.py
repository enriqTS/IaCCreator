from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class RekognitionConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.REKOGNITION] = ServiceType.REKOGNITION
    collection_id: str = TerraformField(
        "faces", description="Face collection identifier"
    )
