"""Values other modules consume from an API Gateway."""

from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_outputs(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate outputs.tf for an API Gateway instance.

    Always outputs: api_id, api_endpoint, execution_arn.
    Conditionally outputs:
    - invoke_url per stage (when stages are configured)
    - domain_name and target_domain_name (when custom domain is configured)
    - authorizer_id per authorizer (when authorizers are configured)
    - vpc_link_id per VPC link (when VPC links are configured)
    """
    parts = [
        r.render_output(
            f"{instance.name}_api_id",
            f"aws_apigatewayv2_api.{instance.name}.id",
            "ID of the API Gateway",
        ),
        r.render_output(
            f"{instance.name}_api_endpoint",
            f"aws_apigatewayv2_api.{instance.name}.api_endpoint",
            "Endpoint URL of the API Gateway",
        ),
        r.render_output(
            f"{instance.name}_execution_arn",
            f"aws_apigatewayv2_api.{instance.name}.execution_arn",
            "Execution ARN of the API Gateway",
        ),
    ]

    # Output invoke_url per stage
    stages = getattr(config, "stages", None)
    if stages is not None:
        for stage_cfg in stages:
            stage_name = stage_cfg.get("name", "$default")
            sanitized_stage = sanitize_route_name(stage_name)
            parts.append(
                r.render_output(
                    f"{instance.name}_{sanitized_stage}_invoke_url",
                    f"aws_apigatewayv2_stage.{instance.name}_{sanitized_stage}_stage.invoke_url",
                    f"Invoke URL for the {stage_name} stage",
                )
            )

    # Output domain_name and target_domain_name for custom domain
    custom_domain = getattr(config, "custom_domain", None)
    if custom_domain is not None:
        parts.append(
            r.render_output(
                f"{instance.name}_domain_name",
                f"aws_apigatewayv2_domain_name.{instance.name}_domain.domain_name",
                "Custom domain name",
            )
        )
        parts.append(
            r.render_output(
                f"{instance.name}_target_domain_name",
                f"aws_apigatewayv2_domain_name.{instance.name}_domain.domain_name_configuration[0].target_domain_name",
                "Target domain name for DNS CNAME record",
            )
        )

    # Output authorizer_id per authorizer
    authorizers = getattr(config, "authorizers", None)
    if authorizers is not None:
        for authorizer in authorizers:
            auth_name = authorizer["name"]
            parts.append(
                r.render_output(
                    f"{instance.name}_{auth_name}_authorizer_id",
                    f"aws_apigatewayv2_authorizer.{instance.name}_{auth_name}_authorizer.id",
                    f"ID of the {auth_name} authorizer",
                )
            )

    # Output vpc_link_id per VPC link
    vpc_links = getattr(config, "vpc_links", None)
    if vpc_links is not None:
        for vpc_link in vpc_links:
            vpc_link_name = vpc_link["name"]
            parts.append(
                r.render_output(
                    f"{instance.name}_{vpc_link_name}_vpc_link_id",
                    f"aws_apigatewayv2_vpc_link.{instance.name}_{vpc_link_name}_vpc_link.id",
                    f"ID of the {vpc_link_name} VPC link",
                )
            )

    return "\n".join(parts)
