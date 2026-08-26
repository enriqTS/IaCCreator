from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import TerraformField


class ManagedPrometheusConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MANAGED_PROMETHEUS] = (
        ServiceType.MANAGED_PROMETHEUS
    )
    alias: str = TerraformField("metrics", description="Prometheus workspace alias")
