from typing import Literal

from pydantic import PrivateAttr

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class OrganizationsConfig(BaseServiceConfig):
    _delegated_service_principals: list[str] = PrivateAttr(default_factory=list)
    service_type: Literal[ServiceType.ORGANIZATIONS] = ServiceType.ORGANIZATIONS
    feature_set: str = TerraformField(
        "ALL",
        description="Organization feature set",
        options=[
            OptionEntry(value="ALL", label="All features"),
            OptionEntry(value="CONSOLIDATED_BILLING", label="Consolidated billing"),
        ],
    )
    enabled_policy_types: list[str] = TerraformField(
        default_factory=lambda: ["SERVICE_CONTROL_POLICY"],
        description="Organization policy types",
    )
    aws_service_access_principals: list[str] = TerraformField(
        default_factory=list,
        description="Additional trusted service principals to preserve alongside connected security services",
    )
