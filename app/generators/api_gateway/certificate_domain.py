"""Render managed certificate guards and Regional API custom-domain mappings."""

from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.api_gateway_domains import ApiGatewayDomainBinding
from app.models.input_models.api_gateway_config import ApiGatewayConfig


def domain_preconditions(
    binding: ApiGatewayDomainBinding, renderer: HCLRenderer
) -> list[dict[str, object]]:
    hostname = renderer.render_expression(binding.domain_name)
    names = f"var.{binding.certificate_names_input}"
    arn = f"var.{binding.certificate_input}"
    return [
        {
            "condition": Expr(
                f'split(":", {arn})[3] == data.aws_region.api_custom_domains.name'
            ),
            "error_message": "The custom domain and ACM certificate must use the same AWS Region.",
        },
        {
            "condition": Expr(
                f'split(":", {arn})[4] == data.aws_caller_identity.api_custom_domains.account_id'
            ),
            "error_message": "The custom domain and ACM certificate must use the same AWS account.",
        },
        {
            "condition": Expr(
                f'anytrue([for name in {names} : lower(name) == {hostname} || (startswith(lower(name), "*.") && endswith({hostname}, substr(lower(name), 1, length(name) - 1)) && length(split(".", name)) == length(split(".", {hostname})))])'
            ),
            "error_message": "The certificate must cover the custom hostname; wildcard certificates cover only one label.",
        },
    ]


def render_certificate_domain(
    binding: ApiGatewayDomainBinding, config: ApiGatewayConfig, renderer: HCLRenderer
) -> str:
    attrs = {
        "domain_name": binding.domain_name,
        "domain_name_configuration": {
            "certificate_arn": Expr(f"var.{binding.certificate_input}"),
            "endpoint_type": "REGIONAL",
            "security_policy": "TLS_1_2",
        },
        "lifecycle": {"precondition": domain_preconditions(binding, renderer)},
    }
    if config.mutual_tls_truststore_uri:
        attrs["mutual_tls_authentication"] = {
            "truststore_uri": config.mutual_tls_truststore_uri
        }
        if config.mutual_tls_truststore_version:
            attrs["mutual_tls_authentication"]["truststore_version"] = (
                config.mutual_tls_truststore_version
            )
    return renderer.render_resource(
        "aws_apigatewayv2_domain_name", binding.domain_resource, attrs
    )


def render_certificate_mapping(
    binding: ApiGatewayDomainBinding, renderer: HCLRenderer
) -> str:
    stage = sanitize_route_name(binding.stage_name)
    attrs = {
        "api_id": Expr(f"aws_apigatewayv2_api.{binding.gateway_name}.id"),
        "domain_name": Expr(
            f"aws_apigatewayv2_domain_name.{binding.domain_resource}.id"
        ),
        "stage": Expr(
            f"aws_apigatewayv2_stage.{binding.gateway_name}_{stage}_stage.id"
        ),
    }
    if binding.api_mapping_key:
        attrs["api_mapping_key"] = binding.api_mapping_key
    return renderer.render_resource(
        "aws_apigatewayv2_api_mapping", binding.mapping_resource, attrs
    )
