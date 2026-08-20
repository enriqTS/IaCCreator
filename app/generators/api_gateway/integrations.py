"""Backend integrations and rate limiting."""

from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


def render_integrations(
    instance: ResourceInstanceIR, config: ApiGatewayConfig, r: HCLRenderer
) -> str:
    """Generate aws_apigatewayv2_integration resources for each configured integration.

    Supports integration types:
    - HTTP_PROXY: sets integration_type, integration_uri, integration_method
    - HTTP: sets integration_type = "HTTP", integration_uri, integration_method
    - AWS_PROXY (Lambda): sets integration_type = "AWS_PROXY", integration_uri,
      payload_format_version (default "2.0")
    - VPC_LINK: sets connection_type = "VPC_LINK", connection_id referencing VPC link resource

    Also includes optional fields from TerraformField config:
    - connection_type, connection_id, content_handling_strategy, credentials_arn,
      passthrough_behavior, payload_format_version, timeout_milliseconds,
      tls_server_name_to_verify (as tls_config block), integration_subtype
    """
    integrations = getattr(config, "integrations", None)
    if not integrations:
        return ""

    parts: list[str] = []

    for integration in integrations:
        integ_name = integration["name"]
        integ_type = integration.get("type", "HTTP_PROXY")
        resource_name = f"{instance.name}_{integ_name}_integration"

        attrs: dict = {
            "api_id": Expr(f"aws_apigatewayv2_api.{instance.name}.id"),
            "integration_type": integ_type,
        }

        if integ_type == "HTTP_PROXY" or integ_type == "HTTP":
            if integration.get("uri"):
                attrs["integration_uri"] = integration["uri"]
            if integration.get("method"):
                attrs["integration_method"] = integration["method"]

        elif integ_type == "AWS_PROXY":
            if integration.get("uri"):
                attrs["integration_uri"] = integration["uri"]
            payload_version = integration.get("payload_format_version", "2.0")
            attrs["payload_format_version"] = payload_version

        # VPC_LINK connection attributes (can apply to any integration type)
        vpc_link_name = integration.get("vpc_link_name")
        if vpc_link_name:
            attrs["connection_type"] = "VPC_LINK"
            attrs["connection_id"] = Expr(
                f"aws_apigatewayv2_vpc_link.{instance.name}_{vpc_link_name}_vpc_link.id"
            )

        # New optional integration fields from TerraformField config
        # Use per-integration dict values first, then fall back to top-level config fields
        connection_type = integration.get("connection_type")
        if connection_type is None and not vpc_link_name:
            connection_type = getattr(config, "connection_type", None)
        if connection_type is not None and "connection_type" not in attrs:
            attrs["connection_type"] = connection_type

        connection_id = integration.get("connection_id")
        if connection_id is None and not vpc_link_name:
            connection_id = getattr(config, "connection_id", None)
        if connection_id is not None and "connection_id" not in attrs:
            attrs["connection_id"] = connection_id

        content_handling = integration.get("content_handling_strategy")
        if content_handling is None:
            content_handling = getattr(config, "content_handling_strategy", None)
        if content_handling is not None:
            attrs["content_handling_strategy"] = content_handling

        creds_arn = integration.get("credentials_arn")
        if creds_arn is None:
            creds_arn = getattr(config, "credentials_arn", None)
        if creds_arn is not None:
            attrs["credentials_arn"] = Expr("var.credentials_arn")

        passthrough = integration.get("passthrough_behavior")
        if passthrough is None:
            passthrough = getattr(config, "passthrough_behavior", None)
        if passthrough is not None:
            attrs["passthrough_behavior"] = passthrough

        # payload_format_version — only add if not already set above
        pfv = integration.get("payload_format_version")
        if pfv is None and integ_type not in ("AWS_PROXY",):
            pfv = getattr(config, "payload_format_version", None)
        if pfv is not None and "payload_format_version" not in attrs:
            attrs["payload_format_version"] = pfv

        timeout_ms = integration.get("timeout_milliseconds")
        if timeout_ms is None:
            timeout_ms = getattr(config, "timeout_milliseconds", None)
        if timeout_ms is not None:
            attrs["timeout_milliseconds"] = timeout_ms

        # tls_config block with server_name_to_verify
        tls_server_name = integration.get("tls_server_name_to_verify")
        if tls_server_name is None:
            tls_server_name = getattr(config, "tls_server_name_to_verify", None)
        if tls_server_name is not None:
            attrs["tls_config"] = {
                "server_name_to_verify": tls_server_name,
            }

        integ_subtype = integration.get("integration_subtype")
        if integ_subtype is None:
            integ_subtype = getattr(config, "integration_subtype", None)
        if integ_subtype is not None:
            attrs["integration_subtype"] = integ_subtype

        parts.append(
            r.render_resource("aws_apigatewayv2_integration", resource_name, attrs)
        )

    return "\n".join(parts)


def render_variables(config: ApiGatewayConfig, r: HCLRenderer) -> list[str]:
    """Variable blocks this concern contributes."""
    parts: list[str] = []
    # ─── Integrations fields ──────────────────────────────────────────────
    if config.connection_type is not None:
        parts.append(
            r.render_variable(
                "connection_type",
                "string",
                "Connection type for the integration",
                default=config.connection_type,
            )
        )
    if config.connection_id is not None:
        parts.append(
            r.render_variable(
                "connection_id",
                "string",
                "Connection ID for VPC link integrations",
                default=config.connection_id,
            )
        )
    if config.content_handling_strategy is not None:
        parts.append(
            r.render_variable(
                "content_handling_strategy",
                "string",
                "Content handling strategy for the integration",
                default=config.content_handling_strategy,
            )
        )
    if config.credentials_arn is not None:
        parts.append(
            r.render_variable(
                "credentials_arn",
                "string",
                "Credentials ARN for the integration",
                default=config.credentials_arn,
            )
        )
    if config.passthrough_behavior is not None:
        parts.append(
            r.render_variable(
                "passthrough_behavior",
                "string",
                "Passthrough behavior for the integration",
                default=config.passthrough_behavior,
            )
        )
    if config.payload_format_version is not None:
        parts.append(
            r.render_variable(
                "payload_format_version",
                "string",
                "Payload format version for the integration",
                default=config.payload_format_version,
            )
        )
    if config.timeout_milliseconds is not None:
        parts.append(
            r.render_variable(
                "timeout_milliseconds",
                "number",
                "Integration timeout in milliseconds",
                default=config.timeout_milliseconds,
            )
        )
    if config.tls_server_name_to_verify is not None:
        parts.append(
            r.render_variable(
                "tls_server_name_to_verify",
                "string",
                "TLS server name to verify for the integration",
                default=config.tls_server_name_to_verify,
            )
        )
    if config.integration_subtype is not None:
        parts.append(
            r.render_variable(
                "integration_subtype",
                "string",
                "Integration subtype for AWS service integrations",
                default=config.integration_subtype,
            )
        )

    # ─── Rate Limiting fields ─────────────────────────────────────────────
    if config.throttling_burst_limit is not None:
        parts.append(
            r.render_variable(
                "throttling_burst_limit",
                "number",
                "Maximum number of concurrent requests (burst)",
                default=config.throttling_burst_limit,
            )
        )
    if config.throttling_rate_limit is not None:
        parts.append(
            r.render_variable(
                "throttling_rate_limit",
                "number",
                "Maximum number of requests per second (steady-state)",
                default=config.throttling_rate_limit,
            )
        )
    return parts
