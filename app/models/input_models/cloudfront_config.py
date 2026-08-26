"""CloudFront distribution configuration model."""

from typing import Literal

from app.models.input_models._base import BaseServiceConfig
from app.models.input_models._general import ServiceType
from app.models.input_models._metadata import OptionEntry, TerraformField


class CloudFrontConfig(BaseServiceConfig):
    service_type: Literal[ServiceType.CLOUDFRONT] = ServiceType.CLOUDFRONT
    origin_domain_name: str = TerraformField("", description="Origin DNS domain name")
    origin_id: str = TerraformField("primary-origin", description="Origin identifier")
    enabled: bool = TerraformField(True, description="Enable the distribution")
    default_root_object: str | None = TerraformField(
        "index.html", description="Default root object"
    )
    viewer_protocol_policy: str = TerraformField(
        "redirect-to-https",
        description="Viewer protocol policy",
        options=[
            OptionEntry(value="allow-all", label="Allow all"),
            OptionEntry(value="https-only", label="HTTPS only"),
            OptionEntry(value="redirect-to-https", label="Redirect to HTTPS"),
        ],
    )
    price_class: str = TerraformField(
        "PriceClass_100",
        description="Edge location price class",
        options=[
            OptionEntry(value=value, label=value)
            for value in ("PriceClass_100", "PriceClass_200", "PriceClass_All")
        ],
    )
