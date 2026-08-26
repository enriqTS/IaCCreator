from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class ManagedGrafanaConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.MANAGED_GRAFANA] = ServiceType.MANAGED_GRAFANA
    workspace_name: str = TerraformField(
        "observability", description="Grafana workspace name"
    )
    account_access_type: str = TerraformField(
        "CURRENT_ACCOUNT",
        description="Account access type",
        options=[
            OptionEntry(value="CURRENT_ACCOUNT", label="Current account"),
            OptionEntry(value="ORGANIZATION", label="Organization"),
        ],
    )
    authentication_providers: list[str] = TerraformField(
        default_factory=lambda: ["AWS_SSO"], description="Authentication providers"
    )
    permission_type: str = TerraformField(
        "SERVICE_MANAGED",
        description="Workspace permission type",
        options=[
            OptionEntry(value="SERVICE_MANAGED", label="Service managed"),
            OptionEntry(value="CUSTOMER_MANAGED", label="Customer managed"),
        ],
    )
    data_sources: list[str] = TerraformField(
        default_factory=lambda: ["CLOUDWATCH", "PROMETHEUS"],
        description="Enabled AWS data sources",
    )
