"""AWS WAFv2 web ACL configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class WafConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.WAF] = ServiceType.WAF
    description: str | None = TerraformField(None, description="Web ACL description")
    scope: str = TerraformField(
        "REGIONAL",
        description="Deployment scope",
        options=[
            OptionEntry(value="REGIONAL", label="Regional"),
            OptionEntry(value="CLOUDFRONT", label="CloudFront"),
        ],
    )
    default_action: str = TerraformField(
        "allow",
        description="Action for unmatched requests",
        options=[
            OptionEntry(value="allow", label="Allow"),
            OptionEntry(value="block", label="Block"),
        ],
    )
    cloudwatch_metrics_enabled: bool = TerraformField(
        True, description="Publish metrics to CloudWatch"
    )
    sampled_requests_enabled: bool = TerraformField(
        True, description="Store sampled requests"
    )
