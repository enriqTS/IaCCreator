"""Custom domain names and their API mappings."""

from app.generators.api_gateway._support import sanitize_route_name
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_domain(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_domain_name and aws_apigatewayv2_api_mapping resources.

    When a custom_domain block is configured with domain_name and certificate_arn,
    produces:
    - An aws_apigatewayv2_domain_name resource with domain_name_configuration
      containing certificate_arn, endpoint_type, and security_policy.
    - A mutual_tls_authentication block when truststore fields are set.
    - An aws_apigatewayv2_api_mapping resource referencing the API, domain, and stage.

    Returns empty string when no custom_domain is configured.
    """
    custom_domain = getattr(config, "custom_domain", None)
    if not custom_domain:
        return ""

    domain_name = custom_domain.get("domain_name", "")
    certificate_arn = custom_domain.get("certificate_arn", "")

    parts: list[str] = []

    # Resolve endpoint_type and security_policy from custom_domain dict or config fields
    endpoint_type = custom_domain.get("endpoint_type")
    if endpoint_type is None:
        endpoint_type = getattr(config, "endpoint_type", None)
    if endpoint_type is None:
        endpoint_type = "REGIONAL"

    security_policy = custom_domain.get("security_policy")
    if security_policy is None:
        security_policy = getattr(config, "security_policy", None)
    if security_policy is None:
        security_policy = "TLS_1_2"

    # aws_apigatewayv2_domain_name resource
    domain_resource_name = f"{instance.name}_domain"
    domain_attrs: dict = {
        "domain_name": domain_name,
        "domain_name_configuration": {
            "certificate_arn": certificate_arn,
            "endpoint_type": endpoint_type,
            "security_policy": security_policy,
        },
    }

    # mutual_tls_authentication block
    mutual_tls_uri = custom_domain.get("mutual_tls_truststore_uri")
    if mutual_tls_uri is None:
        mutual_tls_uri = getattr(config, "mutual_tls_truststore_uri", None)
    mutual_tls_version = custom_domain.get("mutual_tls_truststore_version")
    if mutual_tls_version is None:
        mutual_tls_version = getattr(config, "mutual_tls_truststore_version", None)

    if mutual_tls_uri is not None:
        mutual_tls_block: dict = {
            "truststore_uri": mutual_tls_uri,
        }
        if mutual_tls_version is not None:
            mutual_tls_block["truststore_version"] = mutual_tls_version
        domain_attrs["mutual_tls_authentication"] = mutual_tls_block

    parts.append(
        r.render_resource(
            "aws_apigatewayv2_domain_name", domain_resource_name, domain_attrs
        )
    )

    # Determine stage reference for the api_mapping
    # Use the first configured stage, or fall back to $default
    stage_resource_ref: str
    stages = getattr(config, "stages", None)
    if stages:
        first_stage_name = stages[0].get("name", "$default")
        sanitized_stage = sanitize_route_name(first_stage_name)
        stage_resource_ref = Expr(
            f"aws_apigatewayv2_stage.{instance.name}_{sanitized_stage}_stage.id"
        )
    else:
        stage_resource_ref = Expr(
            f"aws_apigatewayv2_stage.{instance.name}_default_stage.id"
        )

    # aws_apigatewayv2_api_mapping resource
    mapping_resource_name = f"{instance.name}_api_mapping"
    mapping_attrs: dict = {
        "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
        "domain_name": Expr(f"aws_apigatewayv2_domain_name.{domain_resource_name}.id"),
        "stage": stage_resource_ref,
    }
    parts.append(
        r.render_resource(
            "aws_apigatewayv2_api_mapping", mapping_resource_name, mapping_attrs
        )
    )

    return "\n".join(parts)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = []
    # ─── Custom Domain fields ─────────────────────────────────────────────
    if config.endpoint_type is not None:
        parts.append(
            r.render_variable(
                "endpoint_type",
                "string",
                "Endpoint type for the custom domain",
                default=config.endpoint_type,
            )
        )
    if config.security_policy is not None:
        parts.append(
            r.render_variable(
                "security_policy",
                "string",
                "TLS security policy for the custom domain",
                default=config.security_policy,
            )
        )
    if config.mutual_tls_truststore_uri is not None:
        parts.append(
            r.render_variable(
                "mutual_tls_truststore_uri",
                "string",
                "S3 URI of the truststore for mutual TLS authentication",
                default=config.mutual_tls_truststore_uri,
            )
        )
    if config.mutual_tls_truststore_version is not None:
        parts.append(
            r.render_variable(
                "mutual_tls_truststore_version",
                "string",
                "Version of the truststore for mutual TLS authentication",
                default=config.mutual_tls_truststore_version,
            )
        )
    return parts
