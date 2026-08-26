"""Amazon Keyspaces keyspace configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class KeyspacesConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.KEYSPACES] = ServiceType.KEYSPACES
    keyspace_name: str = TerraformField("application", description="Keyspace name")
