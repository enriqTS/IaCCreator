from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class TranscribeConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.TRANSCRIBE] = ServiceType.TRANSCRIBE
    vocabulary_name: str = TerraformField(
        "custom-vocabulary", description="Vocabulary name"
    )
    language_code: str = TerraformField("en-US", description="Vocabulary language code")
    phrases: list[str] = TerraformField(
        default_factory=list, description="Words and phrases in the vocabulary"
    )
