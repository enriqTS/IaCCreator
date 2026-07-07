"""OpenSearch-specific configuration model."""

from typing import Literal, Optional

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType


class OpenSearchConfig(BaseServiceConfig):
    """OpenSearch-specific configuration."""

    service_type: Literal[ServiceType.OPENSEARCH] = ServiceType.OPENSEARCH
    opensearch_domain_name: Optional[str] = None
