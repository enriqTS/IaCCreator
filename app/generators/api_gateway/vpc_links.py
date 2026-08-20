"""VPC links for private integrations."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_vpc_links(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_vpc_link resources for each configured VPC link.

    Each VPC link resource includes name, subnet_ids, and security_group_ids.
    Returns empty string when no VPC links are configured.
    """
    vpc_links = getattr(config, "vpc_links", None)
    if not vpc_links:
        return ""

    parts: list[str] = []

    for vpc_link in vpc_links:
        vpc_link_name = vpc_link["name"]
        resource_name = f"{instance.name}_{vpc_link_name}_vpc_link"

        attrs: dict = {
            "name": vpc_link_name,
            "subnet_ids": vpc_link["subnet_ids"],
            "security_group_ids": vpc_link["security_group_ids"],
        }

        parts.append(
            r.render_resource("aws_apigatewayv2_vpc_link", resource_name, attrs)
        )

    return "\n".join(parts)
