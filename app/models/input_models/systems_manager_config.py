from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class SystemsManagerConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.SYSTEMS_MANAGER] = ServiceType.SYSTEMS_MANAGER
    document_name: str = TerraformField(
        "managed-document", description="Systems Manager document name"
    )
    document_type: str = TerraformField(
        "Command",
        description="Document type",
        options=[
            OptionEntry(value="Command", label="Command"),
            OptionEntry(value="Automation", label="Automation"),
            OptionEntry(value="Policy", label="Policy"),
        ],
    )
    document_format: str = TerraformField(
        "JSON",
        description="Document format",
        options=[
            OptionEntry(value="JSON", label="JSON"),
            OptionEntry(value="YAML", label="YAML"),
        ],
    )
    content: str = TerraformField(
        '{"schemaVersion":"2.2","description":"Managed by IaCCreator","mainSteps":[]}',
        description="Document body",
    )
