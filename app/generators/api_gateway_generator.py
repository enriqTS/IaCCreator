"""API Gateway service generator — produces HCL for aws_apigatewayv2_api resources."""

from app.generators.api_gateway_validator import APIGatewayValidator
from app.generators.base import get_typed_config
from app.generators.connection_helpers import generate_connection_variables
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.api_gateway_config import ApiGatewayConfig
from app.models.ir_models import ResourceInstanceIR


class APIGatewayGenerator:
    """Generates Terraform files for API Gateway (HTTP API) resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()
        self._validator = APIGatewayValidator()

    def _resolve_config(self, instance: ResourceInstanceIR) -> ApiGatewayConfig:
        """Resolve instance config to ApiGatewayConfig.

        Uses get_typed_config when the config is already an ApiGatewayConfig.
        Falls back to duck-typed access if field names match.
        """
        try:
            return get_typed_config(instance, ApiGatewayConfig)
        except Exception:
            # Fallback: duck-typed access works if field names match.
            return instance.config  # type: ignore[return-value]

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate all API Gateway resources as HCL.

        Validates the instance configuration, then composes output from all
        private sub-generators. Returns joined HCL string, filtering empty parts.
        """
        errors = self._validator.validate(instance)
        if errors:
            error_messages = [f"[{e.code}] {e.field}: {e.message}" for e in errors]
            raise ValueError(
                f"API Gateway validation failed with {len(errors)} error(s):\n"
                + "\n".join(error_messages)
            )

        config = self._resolve_config(instance)

        parts = [
            self._generate_api_resource(instance),
            self._generate_api_keys(instance),
        ]

        # Only include routes/stages/authorizers/domain/vpc_links/integrations
        # when the corresponding config fields are explicitly set (not None).
        # This preserves backward compatibility: configs with only the original
        # 7 fields produce only the API resource block.
        if getattr(config, "routes", None) is not None or config.api_key_required:
            parts.append(self._generate_routes(instance))
        if getattr(config, "stages", None) is not None:
            parts.append(self._generate_stages(instance))
        if getattr(config, "authorizers", None) is not None:
            parts.append(self._generate_authorizers(instance))
        if getattr(config, "custom_domain", None) is not None:
            parts.append(self._generate_domain(instance))
        if getattr(config, "vpc_links", None) is not None:
            parts.append(self._generate_vpc_links(instance))
        if getattr(config, "integrations", None) is not None:
            parts.append(self._generate_integrations(instance))

        return "\n".join(p for p in parts if p)

    def _generate_api_resource(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_api resource block."""
        config = self._resolve_config(instance)
        attrs: dict = {
            "name": "var.api_name",
            "protocol_type": "var.protocol_type",
        }
        if config.description is not None:
            attrs["description"] = "var.description"
        if config.cors_configuration is not None:
            attrs["cors_configuration"] = "var.cors_configuration"
        if config.disable_execute_api_endpoint is not None:
            attrs["disable_execute_api_endpoint"] = "var.disable_execute_api_endpoint"
        # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
        if config.protocol_type == "WEBSOCKET":
            if config.route_selection_expression is not None:
                attrs["route_selection_expression"] = "var.route_selection_expression"
        if config.tags is not None:
            attrs["tags"] = "var.tags"

        # API key selection expression when api_key_required is true
        if config.api_key_required:
            attrs["api_key_selection_expression"] = "$request.header.x-api-key"

        # API key selection expression for WEBSOCKET with api_keys list
        api_keys = getattr(config, "api_keys", None)
        if api_keys and config.protocol_type == "WEBSOCKET" and not config.api_key_required:
            attrs["api_key_selection_expression"] = "$request.header.x-api-key"

        # New General-level optional fields
        if config.api_key_selection_expression is not None and not config.api_key_required:
            attrs["api_key_selection_expression"] = "var.api_key_selection_expression"
        if config.ip_address_type is not None:
            attrs["ip_address_type"] = "var.ip_address_type"
        if config.version is not None:
            attrs["version"] = "var.version"
        if config.body is not None:
            attrs["body"] = "var.body"
        if config.fail_on_warnings is not None:
            attrs["fail_on_warnings"] = "var.fail_on_warnings"

        # Mutual TLS authentication block
        mutual_tls = getattr(config, "mutual_tls_authentication", None)
        if mutual_tls and mutual_tls.get("truststore_uri"):
            mutual_tls_block: dict = {
                "truststore_uri": mutual_tls["truststore_uri"],
            }
            if mutual_tls.get("truststore_version"):
                mutual_tls_block["truststore_version"] = mutual_tls["truststore_version"]
            attrs["mutual_tls_authentication"] = mutual_tls_block

        return self._r.render_resource("aws_apigatewayv2_api", instance.name, attrs)

    def _generate_api_keys(self, instance: ResourceInstanceIR) -> str:
        """Generate API key resources based on protocol type and configured keys.

        - If `api_keys` list is configured, generates one resource per key:
          - HTTP protocol: emits `aws_api_gateway_api_key` (REST v1 type) with a warning comment
          - WEBSOCKET protocol: emits `aws_apigatewayv2_api_key` resources
        - Falls back to legacy behavior (single key) when only `api_key_required` is set
          without an explicit `api_keys` list.
        """
        config = self._resolve_config(instance)
        api_keys = getattr(config, "api_keys", None)

        # Use the api_keys list if available
        if api_keys:
            protocol_type = config.protocol_type or "HTTP"
            parts: list[str] = []

            if protocol_type == "HTTP":
                # HTTP APIs do not natively support API keys — emit REST v1 resource type
                # with a warning comment
                comment = (
                    "# NOTE: HTTP APIs do not natively support API keys. "
                    "Consider using a Lambda authorizer.\n"
                )
                parts.append(comment)
                for key in api_keys:
                    key_name = key.get("name", f"{instance.name}-api-key")
                    sanitized_key_name = self._sanitize_route_name(key_name)
                    resource_name = f"{instance.name}_{sanitized_key_name}_api_key"
                    attrs: dict = {
                        "name": key_name,
                    }
                    if key.get("description"):
                        attrs["description"] = key["description"]
                    if key.get("value"):
                        attrs["value"] = key["value"]
                    parts.append(
                        self._r.render_resource(
                            "aws_api_gateway_api_key", resource_name, attrs
                        )
                    )
            else:
                # WEBSOCKET — api_key_selection_expression is set on the API resource
                # (handled in _generate_api_resource), generate aws_apigatewayv2_api_key blocks
                for key in api_keys:
                    key_name = key.get("name", f"{instance.name}-api-key")
                    sanitized_key_name = self._sanitize_route_name(key_name)
                    resource_name = f"{instance.name}_{sanitized_key_name}_api_key"
                    attrs = {
                        "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                        "name": key_name,
                    }
                    if key.get("description"):
                        attrs["description"] = key["description"]
                    if key.get("value"):
                        attrs["value"] = key["value"]
                    parts.append(
                        self._r.render_resource(
                            "aws_apigatewayv2_api_key", resource_name, attrs
                        )
                    )

            return "\n".join(parts)

        # Legacy fallback: single key when api_key_required is set without api_keys list
        if not config.api_key_required:
            return ""

        attrs = {
            "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
            "name": f"{instance.name}-api-key",
        }
        return self._r.render_resource(
            "aws_apigatewayv2_api_key", f"{instance.name}_api_key", attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an API Gateway instance.

        Emits variable blocks for all TerraformField-annotated fields on the config.
        - api_name and protocol_type are required → no default value
        - All others are optional → include default when non-None
        """
        config = self._resolve_config(instance)
        parts = [
            # Required fields — no default
            self._r.render_variable("api_name", "string", "Name of the API Gateway"),
            self._r.render_variable(
                "protocol_type", "string", "API protocol type"
            ),
        ]

        # ─── General optional fields ─────────────────────────────────────────
        if config.description is not None:
            parts.append(
                self._r.render_variable(
                    "description",
                    "string",
                    "Description of the API",
                    default=config.description,
                )
            )
        if config.api_key_selection_expression is not None:
            parts.append(
                self._r.render_variable(
                    "api_key_selection_expression",
                    "string",
                    "API key selection expression for the API",
                    default=config.api_key_selection_expression,
                )
            )
        if config.ip_address_type is not None:
            parts.append(
                self._r.render_variable(
                    "ip_address_type",
                    "string",
                    "IP address type for the API endpoint",
                    default=config.ip_address_type,
                )
            )
        if config.version is not None:
            parts.append(
                self._r.render_variable(
                    "version",
                    "string",
                    "Version identifier for the API",
                    default=config.version,
                )
            )
        if config.body is not None:
            parts.append(
                self._r.render_variable(
                    "body",
                    "string",
                    "OpenAPI specification body for the API",
                    default=config.body,
                )
            )
        if config.fail_on_warnings is not None:
            parts.append(
                self._r.render_variable(
                    "fail_on_warnings",
                    "bool",
                    "Whether to roll back the API creation when a warning is encountered",
                    default=config.fail_on_warnings,
                )
            )

        # ─── Routes fields ────────────────────────────────────────────────────
        if config.cors_configuration is not None:
            parts.append(
                self._r.render_variable(
                    "cors_configuration",
                    "map(string)",
                    "CORS configuration for the API",
                )
            )
        if config.disable_execute_api_endpoint is not None:
            parts.append(
                self._r.render_variable(
                    "disable_execute_api_endpoint",
                    "bool",
                    "Disable the default execute-api endpoint",
                    default=config.disable_execute_api_endpoint,
                )
            )
        # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
        if config.protocol_type == "WEBSOCKET":
            if config.route_selection_expression is not None:
                parts.append(
                    self._r.render_variable(
                        "route_selection_expression",
                        "string",
                        "Route selection expression for WebSocket APIs",
                        default=config.route_selection_expression,
                    )
                )
        if config.authorization_type is not None:
            parts.append(
                self._r.render_variable(
                    "authorization_type",
                    "string",
                    "Authorization type for the route",
                    default=config.authorization_type,
                )
            )
        if config.authorization_scopes is not None:
            parts.append(
                self._r.render_variable(
                    "authorization_scopes",
                    "list(string)",
                    "Authorization scopes for the route",
                    default=config.authorization_scopes,
                )
            )
        if config.operation_name is not None:
            parts.append(
                self._r.render_variable(
                    "operation_name",
                    "string",
                    "Operation name for the route",
                    default=config.operation_name,
                )
            )
        if config.model_selection_expression is not None:
            parts.append(
                self._r.render_variable(
                    "model_selection_expression",
                    "string",
                    "Model selection expression for the route",
                    default=config.model_selection_expression,
                )
            )
        if config.route_response_selection_expression is not None:
            parts.append(
                self._r.render_variable(
                    "route_response_selection_expression",
                    "string",
                    "Route response selection expression",
                    default=config.route_response_selection_expression,
                )
            )

        # ─── Stages fields ────────────────────────────────────────────────────
        if config.access_log_destination_arn is not None:
            parts.append(
                self._r.render_variable(
                    "access_log_destination_arn",
                    "string",
                    "ARN of the CloudWatch log group for access logging",
                    default=config.access_log_destination_arn,
                )
            )
        if config.access_log_format is not None:
            parts.append(
                self._r.render_variable(
                    "access_log_format",
                    "string",
                    "Access log format string for the stage",
                    default=config.access_log_format,
                )
            )
        if config.default_route_data_trace_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "default_route_data_trace_enabled",
                    "bool",
                    "Whether data trace logging is enabled for the default route",
                    default=config.default_route_data_trace_enabled,
                )
            )
        if config.default_route_detailed_metrics_enabled is not None:
            parts.append(
                self._r.render_variable(
                    "default_route_detailed_metrics_enabled",
                    "bool",
                    "Whether detailed metrics are enabled for the default route",
                    default=config.default_route_detailed_metrics_enabled,
                )
            )
        if config.default_route_logging_level is not None:
            parts.append(
                self._r.render_variable(
                    "default_route_logging_level",
                    "string",
                    "Logging level for the default route",
                    default=config.default_route_logging_level,
                )
            )
        if config.default_route_throttling_burst_limit is not None:
            parts.append(
                self._r.render_variable(
                    "default_route_throttling_burst_limit",
                    "number",
                    "Throttling burst limit for the default route",
                    default=config.default_route_throttling_burst_limit,
                )
            )
        if config.default_route_throttling_rate_limit is not None:
            parts.append(
                self._r.render_variable(
                    "default_route_throttling_rate_limit",
                    "number",
                    "Throttling rate limit for the default route",
                    default=config.default_route_throttling_rate_limit,
                )
            )

        # ─── Authorizers fields ───────────────────────────────────────────────
        if config.authorizer_result_ttl_in_seconds is not None:
            parts.append(
                self._r.render_variable(
                    "authorizer_result_ttl_in_seconds",
                    "number",
                    "Time to live (TTL) for cached authorizer results in seconds",
                    default=config.authorizer_result_ttl_in_seconds,
                )
            )
        if config.enable_simple_responses is not None:
            parts.append(
                self._r.render_variable(
                    "enable_simple_responses",
                    "bool",
                    "Whether to enable simple responses for the authorizer",
                    default=config.enable_simple_responses,
                )
            )
        if config.authorizer_credentials_arn is not None:
            parts.append(
                self._r.render_variable(
                    "authorizer_credentials_arn",
                    "string",
                    "Credentials ARN for the authorizer",
                    default=config.authorizer_credentials_arn,
                )
            )
        if config.identity_sources is not None:
            parts.append(
                self._r.render_variable(
                    "identity_sources",
                    "list(string)",
                    "Identity sources for the authorizer",
                    default=config.identity_sources,
                )
            )

        # ─── Custom Domain fields ─────────────────────────────────────────────
        if config.endpoint_type is not None:
            parts.append(
                self._r.render_variable(
                    "endpoint_type",
                    "string",
                    "Endpoint type for the custom domain",
                    default=config.endpoint_type,
                )
            )
        if config.security_policy is not None:
            parts.append(
                self._r.render_variable(
                    "security_policy",
                    "string",
                    "TLS security policy for the custom domain",
                    default=config.security_policy,
                )
            )
        if config.mutual_tls_truststore_uri is not None:
            parts.append(
                self._r.render_variable(
                    "mutual_tls_truststore_uri",
                    "string",
                    "S3 URI of the truststore for mutual TLS authentication",
                    default=config.mutual_tls_truststore_uri,
                )
            )
        if config.mutual_tls_truststore_version is not None:
            parts.append(
                self._r.render_variable(
                    "mutual_tls_truststore_version",
                    "string",
                    "Version of the truststore for mutual TLS authentication",
                    default=config.mutual_tls_truststore_version,
                )
            )

        # ─── Integrations fields ──────────────────────────────────────────────
        if config.connection_type is not None:
            parts.append(
                self._r.render_variable(
                    "connection_type",
                    "string",
                    "Connection type for the integration",
                    default=config.connection_type,
                )
            )
        if config.connection_id is not None:
            parts.append(
                self._r.render_variable(
                    "connection_id",
                    "string",
                    "Connection ID for VPC link integrations",
                    default=config.connection_id,
                )
            )
        if config.content_handling_strategy is not None:
            parts.append(
                self._r.render_variable(
                    "content_handling_strategy",
                    "string",
                    "Content handling strategy for the integration",
                    default=config.content_handling_strategy,
                )
            )
        if config.credentials_arn is not None:
            parts.append(
                self._r.render_variable(
                    "credentials_arn",
                    "string",
                    "Credentials ARN for the integration",
                    default=config.credentials_arn,
                )
            )
        if config.passthrough_behavior is not None:
            parts.append(
                self._r.render_variable(
                    "passthrough_behavior",
                    "string",
                    "Passthrough behavior for the integration",
                    default=config.passthrough_behavior,
                )
            )
        if config.payload_format_version is not None:
            parts.append(
                self._r.render_variable(
                    "payload_format_version",
                    "string",
                    "Payload format version for the integration",
                    default=config.payload_format_version,
                )
            )
        if config.timeout_milliseconds is not None:
            parts.append(
                self._r.render_variable(
                    "timeout_milliseconds",
                    "number",
                    "Integration timeout in milliseconds",
                    default=config.timeout_milliseconds,
                )
            )
        if config.tls_server_name_to_verify is not None:
            parts.append(
                self._r.render_variable(
                    "tls_server_name_to_verify",
                    "string",
                    "TLS server name to verify for the integration",
                    default=config.tls_server_name_to_verify,
                )
            )
        if config.integration_subtype is not None:
            parts.append(
                self._r.render_variable(
                    "integration_subtype",
                    "string",
                    "Integration subtype for AWS service integrations",
                    default=config.integration_subtype,
                )
            )

        # ─── Rate Limiting fields ─────────────────────────────────────────────
        if config.throttling_burst_limit is not None:
            parts.append(
                self._r.render_variable(
                    "throttling_burst_limit",
                    "number",
                    "Maximum number of concurrent requests (burst)",
                    default=config.throttling_burst_limit,
                )
            )
        if config.throttling_rate_limit is not None:
            parts.append(
                self._r.render_variable(
                    "throttling_rate_limit",
                    "number",
                    "Maximum number of requests per second (steady-state)",
                    default=config.throttling_rate_limit,
                )
            )

        # ─── Metadata fields ──────────────────────────────────────────────────
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the API Gateway",
                )
            )

        # Emit connection-derived variable blocks
        connection_vars = generate_connection_variables(instance, self._r)
        if connection_vars:
            parts.append(connection_vars)

        return "\n".join(parts)

    def _generate_routes(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_route resources for the API Gateway instance.

        For HTTP APIs:
          - Produces a route for each configured entry, or a $default route if none configured.
        For WebSocket APIs:
          - Always produces $connect, $disconnect, $default routes, plus any custom routes.
        Routes referencing authorizers get authorization_type and authorizer_id.
        For WebSocket, only $connect gets authorization attributes (per AWS docs).
        If api_key_required is True, all routes get api_key_required = true.
        """
        config = self._resolve_config(instance)
        protocol_type = config.protocol_type or "HTTP"
        is_websocket = protocol_type == "WEBSOCKET"

        # Build a lookup of authorizer names to their configs for authorization_type resolution
        authorizer_map: dict[str, dict] = {}
        authorizers = getattr(config, "authorizers", None)
        if authorizers:
            for auth in authorizers:
                authorizer_map[auth["name"]] = auth

        # Build a lookup of integration names for target resolution
        integration_names: set[str] = set()
        integrations = getattr(config, "integrations", None)
        if integrations:
            for integ in integrations:
                integration_names.add(integ["name"])

        parts: list[str] = []
        routes = getattr(config, "routes", None)

        if is_websocket:
            # WebSocket: always generate special routes + custom routes
            ws_special_routes = ["$connect", "$disconnect", "$default"]
            custom_routes: list[dict] = []
            if routes:
                custom_routes = routes

            for route_key in ws_special_routes:
                route_name = self._sanitize_route_name(route_key)
                resource_name = f"{instance.name}_{route_name}_route"
                attrs: dict = {
                    "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                    "route_key": route_key,
                }

                # Target integration if available (use $default integration or named)
                target_integration = self._find_ws_route_integration(
                    route_key, routes, instance.name
                )
                if target_integration:
                    attrs["target"] = target_integration

                # Authorization only on $connect
                if route_key == "$connect":
                    self._apply_authorization(
                        attrs,
                        routes,
                        route_key,
                        authorizer_map,
                        instance.name,
                        is_connect=True,
                    )

                # API key required — per-route or config-level
                ws_route_cfg = self._find_route_cfg(routes, route_key)
                if (ws_route_cfg and ws_route_cfg.get("api_key_required")) or config.api_key_required:
                    attrs["api_key_required"] = True

                # New optional route fields from TerraformField config
                self._apply_route_optional_fields(attrs, None, routes, route_key, config)

                parts.append(
                    self._r.render_resource(
                        "aws_apigatewayv2_route", resource_name, attrs
                    )
                )

                # Route response generation for WebSocket special routes
                if ws_route_cfg:
                    route_response_key = ws_route_cfg.get("route_response_key")
                    if route_response_key:
                        response_resource_name = f"{instance.name}_{route_name}_route_response"
                        response_attrs = {
                            "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                            "route_id": f"aws_apigatewayv2_route.{resource_name}.id",
                            "route_response_key": route_response_key,
                        }
                        parts.append(
                            self._r.render_resource(
                                "aws_apigatewayv2_route_response",
                                response_resource_name,
                                response_attrs,
                            )
                        )

            # Custom WebSocket routes (non-special)
            for route_cfg in custom_routes:
                route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
                if route_key in ws_special_routes:
                    continue  # Already handled above
                route_name = self._sanitize_route_name(route_key)
                resource_name = f"{instance.name}_{route_name}_route"
                attrs = {
                    "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                    "route_key": route_key,
                }

                # Target integration
                integration_name = route_cfg.get("integration_name")
                if integration_name and integration_name in integration_names:
                    attrs["target"] = (
                        f"integrations/${{aws_apigatewayv2_integration."
                        f"{instance.name}_{integration_name}_integration.id}}"
                    )

                # WebSocket non-$connect routes do NOT get authorization (Property 4)

                # API key required — per-route or config-level
                if route_cfg.get("api_key_required") or config.api_key_required:
                    attrs["api_key_required"] = True

                # New optional route fields from TerraformField config
                self._apply_route_optional_fields(attrs, route_cfg, routes, route_key, config)

                parts.append(
                    self._r.render_resource(
                        "aws_apigatewayv2_route", resource_name, attrs
                    )
                )

                # Route response generation for custom WebSocket routes
                route_response_key = route_cfg.get("route_response_key")
                if route_response_key:
                    response_resource_name = f"{instance.name}_{route_name}_route_response"
                    response_attrs = {
                        "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                        "route_id": f"aws_apigatewayv2_route.{resource_name}.id",
                        "route_response_key": route_response_key,
                    }
                    parts.append(
                        self._r.render_resource(
                            "aws_apigatewayv2_route_response",
                            response_resource_name,
                            response_attrs,
                        )
                    )

        else:
            # HTTP API
            if routes:
                for route_cfg in routes:
                    method = route_cfg.get("method", "ANY")
                    path = route_cfg.get("path", "/")
                    route_key = f"{method} {path}"
                    route_name = self._sanitize_route_name(f"{method}_{path}")
                    resource_name = f"{instance.name}_{route_name}_route"

                    attrs = {
                        "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                        "route_key": route_key,
                    }

                    # Target integration
                    integration_name = route_cfg.get("integration_name")
                    if integration_name and integration_name in integration_names:
                        attrs["target"] = (
                            f"integrations/${{aws_apigatewayv2_integration."
                            f"{instance.name}_{integration_name}_integration.id}}"
                        )

                    # Authorization
                    authorizer_name = route_cfg.get("authorizer_name")
                    if authorizer_name and authorizer_name in authorizer_map:
                        auth_cfg = authorizer_map[authorizer_name]
                        auth_type = auth_cfg.get("type", "JWT")
                        if auth_type in ("JWT", "COGNITO_USER_POOLS"):
                            attrs["authorization_type"] = "JWT"
                        elif auth_type == "REQUEST":
                            attrs["authorization_type"] = "CUSTOM"
                        attrs["authorizer_id"] = (
                            f"aws_apigatewayv2_authorizer."
                            f"{instance.name}_{authorizer_name}_authorizer.id"
                        )

                    # API key required — per-route or config-level
                    if route_cfg.get("api_key_required") or config.api_key_required:
                        attrs["api_key_required"] = True

                    # New optional route fields from TerraformField config
                    self._apply_route_optional_fields(attrs, route_cfg, routes, route_key, config)

                    parts.append(
                        self._r.render_resource(
                            "aws_apigatewayv2_route", resource_name, attrs
                        )
                    )

                    # Route response generation when route_response_key is present
                    route_response_key = route_cfg.get("route_response_key")
                    if route_response_key:
                        response_resource_name = f"{instance.name}_{route_name}_route_response"
                        response_attrs = {
                            "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                            "route_id": f"aws_apigatewayv2_route.{resource_name}.id",
                            "route_response_key": route_response_key,
                        }
                        parts.append(
                            self._r.render_resource(
                                "aws_apigatewayv2_route_response",
                                response_resource_name,
                                response_attrs,
                            )
                        )
            else:
                # No routes configured — generate $default route
                resource_name = f"{instance.name}_default_route"
                attrs = {
                    "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                    "route_key": "$default",
                }

                # API key required
                if config.api_key_required:
                    attrs["api_key_required"] = True

                # New optional route fields from TerraformField config
                self._apply_route_optional_fields(attrs, None, routes, "$default", config)

                parts.append(
                    self._r.render_resource(
                        "aws_apigatewayv2_route", resource_name, attrs
                    )
                )

        return "\n".join(parts)

    def _sanitize_route_name(self, name: str) -> str:
        """Sanitize a route name for use as a Terraform resource name.

        Replaces special characters with underscores and strips leading/trailing underscores.
        """
        import re

        # Replace $ with empty, replace non-alphanumeric with underscore
        sanitized = (
            name.replace("$", "").replace("/", "_").replace("{", "").replace("}", "")
        )
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)
        # Collapse multiple underscores and strip leading/trailing
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized.strip("_")

    def _find_ws_route_integration(
        self, route_key: str, routes: list[dict] | None, instance_name: str
    ) -> str | None:
        """Find the integration target for a WebSocket special route."""
        if not routes:
            return None
        for route_cfg in routes:
            cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
            if cfg_route_key == route_key:
                integration_name = route_cfg.get("integration_name")
                if integration_name:
                    return (
                        f"integrations/${{aws_apigatewayv2_integration."
                        f"{instance_name}_{integration_name}_integration.id}}"
                    )
        return None

    def _find_route_cfg(
        self, routes: list[dict] | None, route_key: str
    ) -> dict | None:
        """Find a route config dict by route_key from the routes list."""
        if not routes:
            return None
        for route_cfg in routes:
            cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
            if cfg_route_key == route_key:
                return route_cfg
        return None

    def _apply_authorization(
        self,
        attrs: dict,
        routes: list[dict] | None,
        route_key: str,
        authorizer_map: dict[str, dict],
        instance_name: str,
        is_connect: bool = False,
    ) -> None:
        """Apply authorization attributes to a route if configured.

        For WebSocket, only $connect gets authorization (is_connect=True).
        """
        if not routes:
            return
        for route_cfg in routes:
            cfg_route_key = route_cfg.get("path", route_cfg.get("route_key", ""))
            if cfg_route_key == route_key:
                authorizer_name = route_cfg.get("authorizer_name")
                if authorizer_name and authorizer_name in authorizer_map:
                    auth_cfg = authorizer_map[authorizer_name]
                    auth_type = auth_cfg.get("type", "JWT")
                    if auth_type in ("JWT", "COGNITO_USER_POOLS"):
                        attrs["authorization_type"] = "JWT"
                    elif auth_type == "REQUEST":
                        attrs["authorization_type"] = "CUSTOM"
                    attrs["authorizer_id"] = (
                        f"aws_apigatewayv2_authorizer."
                        f"{instance_name}_{authorizer_name}_authorizer.id"
                    )
                break

    def _apply_route_optional_fields(
        self,
        attrs: dict,
        route_cfg: dict | None,
        routes: list[dict] | None,
        route_key: str,
        config: "ApiGatewayConfig",
    ) -> None:
        """Apply optional route fields from route dict or top-level config TerraformFields.

        Adds authorization_type, authorization_scopes, operation_name,
        model_selection_expression, and route_response_selection_expression
        when they are set (per-route dict takes precedence over config-level fields).
        Does NOT override authorization_type if already set by authorizer logic.
        """
        # authorization_type — only if not already set by the authorizer logic
        if "authorization_type" not in attrs:
            auth_type = (route_cfg or {}).get("authorization_type")
            if auth_type is None:
                auth_type = getattr(config, "authorization_type", None)
            if auth_type is not None:
                attrs["authorization_type"] = auth_type

        # authorization_scopes
        auth_scopes = (route_cfg or {}).get("authorization_scopes")
        if auth_scopes is None:
            auth_scopes = getattr(config, "authorization_scopes", None)
        if auth_scopes is not None:
            attrs["authorization_scopes"] = auth_scopes

        # operation_name
        op_name = (route_cfg or {}).get("operation_name")
        if op_name is None:
            op_name = getattr(config, "operation_name", None)
        if op_name is not None:
            attrs["operation_name"] = op_name

        # model_selection_expression
        model_sel = (route_cfg or {}).get("model_selection_expression")
        if model_sel is None:
            model_sel = getattr(config, "model_selection_expression", None)
        if model_sel is not None:
            attrs["model_selection_expression"] = model_sel

        # route_response_selection_expression
        route_resp_sel = (route_cfg or {}).get("route_response_selection_expression")
        if route_resp_sel is None:
            route_resp_sel = getattr(config, "route_response_selection_expression", None)
        if route_resp_sel is not None:
            attrs["route_response_selection_expression"] = route_resp_sel

    def _generate_stages(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_stage resources and associated CloudWatch log groups.

        For each configured stage, produces:
        - An aws_apigatewayv2_stage resource with auto_deploy, stage_variables,
          default_route_settings (throttling, data trace, detailed metrics, logging level),
          route_settings (per-route throttling), and access_log_settings when logging is enabled.
        - An aws_cloudwatch_log_group resource when access logging is enabled.

        When no stages are configured, generates a single $default stage with auto_deploy=true.
        Also uses top-level TerraformField stage fields (access_log_destination_arn,
        default_route_data_trace_enabled, default_route_detailed_metrics_enabled,
        default_route_logging_level, default_route_throttling_burst_limit,
        default_route_throttling_rate_limit) when the stage dict doesn't override them.
        """
        config = self._resolve_config(instance)
        stages = getattr(config, "stages", None)

        # Default log format per requirement 6.4
        default_log_format = (
            '{"requestId":"$context.requestId",'
            '"ip":"$context.identity.sourceIp",'
            '"requestTime":"$context.requestTime",'
            '"httpMethod":"$context.httpMethod",'
            '"routeKey":"$context.routeKey",'
            '"status":"$context.status",'
            '"protocol":"$context.protocol"}'
        )

        # If no stages configured, generate a single $default stage with auto_deploy
        if not stages:
            stages = [{"name": "$default", "auto_deploy": True}]

        parts: list[str] = []

        for stage_cfg in stages:
            stage_name = stage_cfg.get("name", "$default")
            sanitized_name = self._sanitize_route_name(stage_name)
            resource_name = f"{instance.name}_{sanitized_name}_stage"

            attrs: dict = {
                "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                "name": stage_name,
            }

            # auto_deploy
            auto_deploy = stage_cfg.get("auto_deploy", False)
            if auto_deploy:
                attrs["auto_deploy"] = True

            # stage_variables block
            stage_variables = stage_cfg.get("stage_variables")
            if stage_variables:
                attrs["stage_variables"] = stage_variables

            # default_route_settings block (throttling + data trace + detailed metrics + logging level)
            throttling_burst = stage_cfg.get("throttling_burst_limit")
            throttling_rate = stage_cfg.get("throttling_rate_limit")
            data_trace = stage_cfg.get("data_trace_enabled")
            detailed_metrics = stage_cfg.get("detailed_metrics_enabled")
            logging_level = stage_cfg.get("logging_level")

            # Fall back to top-level TerraformField values from config
            if throttling_burst is None:
                throttling_burst = getattr(config, "default_route_throttling_burst_limit", None)
            if throttling_rate is None:
                throttling_rate = getattr(config, "default_route_throttling_rate_limit", None)
            if data_trace is None:
                data_trace = getattr(config, "default_route_data_trace_enabled", None)
            if detailed_metrics is None:
                detailed_metrics = getattr(config, "default_route_detailed_metrics_enabled", None)
            if logging_level is None:
                logging_level = getattr(config, "default_route_logging_level", None)

            if any(v is not None for v in [throttling_burst, throttling_rate, data_trace, detailed_metrics, logging_level]):
                default_route_settings: dict = {}
                if throttling_burst is not None:
                    default_route_settings["throttling_burst_limit"] = throttling_burst
                if throttling_rate is not None:
                    default_route_settings["throttling_rate_limit"] = throttling_rate
                if data_trace is not None:
                    default_route_settings["data_trace_enabled"] = data_trace
                if detailed_metrics is not None:
                    default_route_settings["detailed_metrics_enabled"] = detailed_metrics
                if logging_level is not None:
                    default_route_settings["logging_level"] = logging_level
                attrs["default_route_settings"] = default_route_settings

            # route_settings blocks for per-route throttling
            route_throttling = stage_cfg.get("route_throttling")
            if route_throttling:
                route_settings_list = []
                for rt in route_throttling:
                    route_key = rt.get("route_key", "$default")
                    rs_attrs: dict = {"route_key": route_key}
                    if "burst" in rt:
                        rs_attrs["throttling_burst_limit"] = rt["burst"]
                    if "rate" in rt:
                        rs_attrs["throttling_rate_limit"] = rt["rate"]
                    route_settings_list.append(rs_attrs)
                attrs["route_settings"] = route_settings_list

            # access_log_settings block — from stage dict or top-level config field
            access_logging_enabled = stage_cfg.get("access_logging_enabled", False)
            access_log_dest_arn = stage_cfg.get("access_log_destination_arn")
            if access_log_dest_arn is None:
                access_log_dest_arn = getattr(config, "access_log_destination_arn", None)

            if access_logging_enabled or access_log_dest_arn is not None:
                log_format = stage_cfg.get("access_log_format")
                if log_format is None:
                    log_format = getattr(config, "access_log_format", None)
                if log_format is None:
                    log_format = default_log_format

                if access_log_dest_arn is not None:
                    # Use the explicit destination ARN from config
                    attrs["access_log_settings"] = {
                        "destination_arn": "var.access_log_destination_arn",
                        "format": log_format,
                    }
                else:
                    # Generate a CloudWatch log group reference
                    log_group_resource_name = f"{instance.name}_{sanitized_name}_log_group"
                    attrs["access_log_settings"] = {
                        "destination_arn": f"aws_cloudwatch_log_group.{log_group_resource_name}.arn",
                        "format": log_format,
                    }

            parts.append(
                self._r.render_resource("aws_apigatewayv2_stage", resource_name, attrs)
            )

            # Generate CloudWatch log group when access logging is enabled via stage dict
            # (not when using explicit access_log_destination_arn)
            if access_logging_enabled and access_log_dest_arn is None:
                log_group_resource_name = f"{instance.name}_{sanitized_name}_log_group"
                retention_days = stage_cfg.get("access_log_retention_days", 30)
                log_group_attrs: dict = {
                    "name": f"/aws/apigateway/{instance.name}/{sanitized_name}",
                    "retention_in_days": retention_days,
                }
                parts.append(
                    self._r.render_resource(
                        "aws_cloudwatch_log_group",
                        log_group_resource_name,
                        log_group_attrs,
                    )
                )

        return "\n".join(parts)

    def _generate_authorizers(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_authorizer resources for each configured authorizer.

        Supports three authorizer types:
        - JWT: authorizer_type = "JWT" with jwt_configuration block (issuer + audience)
        - REQUEST (Lambda): authorizer_type = "REQUEST" with authorizer_uri and payload_format_version
        - COGNITO_USER_POOLS: authorizer_type = "JWT" with jwt_configuration using
          cognito_user_pool_endpoint as issuer and cognito_client_ids as audience

        Also includes optional fields from TerraformField config:
        - authorizer_result_ttl_in_seconds
        - enable_simple_responses
        - authorizer_credentials_arn
        - identity_sources
        """
        config = self._resolve_config(instance)
        authorizers = getattr(config, "authorizers", None)
        if not authorizers:
            return ""

        parts: list[str] = []

        for authorizer in authorizers:
            auth_name = authorizer["name"]
            auth_type = authorizer.get("type", "JWT")
            resource_name = f"{instance.name}_{auth_name}_authorizer"

            attrs: dict = {
                "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
                "name": auth_name,
            }

            if auth_type == "JWT":
                attrs["authorizer_type"] = "JWT"
                jwt_config: dict = {}
                if authorizer.get("issuer"):
                    jwt_config["issuer"] = authorizer["issuer"]
                if authorizer.get("audience"):
                    jwt_config["audience"] = authorizer["audience"]
                if jwt_config:
                    attrs["jwt_configuration"] = jwt_config

            elif auth_type == "REQUEST":
                attrs["authorizer_type"] = "REQUEST"
                if authorizer.get("lambda_arn"):
                    attrs["authorizer_uri"] = authorizer["lambda_arn"]
                payload_version = authorizer.get("payload_format_version", "2.0")
                attrs["authorizer_payload_format_version"] = payload_version

            elif auth_type == "COGNITO_USER_POOLS":
                attrs["authorizer_type"] = "JWT"
                jwt_config = {}
                if authorizer.get("cognito_user_pool_endpoint"):
                    jwt_config["issuer"] = authorizer["cognito_user_pool_endpoint"]
                if authorizer.get("cognito_client_ids"):
                    jwt_config["audience"] = authorizer["cognito_client_ids"]
                if jwt_config:
                    attrs["jwt_configuration"] = jwt_config

            # New optional authorizer fields from TerraformField config
            # Use per-authorizer dict values first, then fall back to top-level config fields
            result_ttl = authorizer.get("authorizer_result_ttl_in_seconds")
            if result_ttl is None:
                result_ttl = getattr(config, "authorizer_result_ttl_in_seconds", None)
            if result_ttl is not None:
                attrs["authorizer_result_ttl_in_seconds"] = result_ttl

            enable_simple = authorizer.get("enable_simple_responses")
            if enable_simple is None:
                enable_simple = getattr(config, "enable_simple_responses", None)
            if enable_simple is not None:
                attrs["enable_simple_responses"] = enable_simple

            creds_arn = authorizer.get("authorizer_credentials_arn")
            if creds_arn is None:
                creds_arn = getattr(config, "authorizer_credentials_arn", None)
            if creds_arn is not None:
                attrs["authorizer_credentials_arn"] = "var.authorizer_credentials_arn"

            identity_src = authorizer.get("identity_sources")
            if identity_src is None:
                identity_src = getattr(config, "identity_sources", None)
            if identity_src is not None:
                attrs["identity_sources"] = identity_src

            parts.append(
                self._r.render_resource(
                    "aws_apigatewayv2_authorizer", resource_name, attrs
                )
            )

        return "\n".join(parts)

    def _generate_domain(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_domain_name and aws_apigatewayv2_api_mapping resources.

        When a custom_domain block is configured with domain_name and certificate_arn,
        produces:
        - An aws_apigatewayv2_domain_name resource with domain_name_configuration
          containing certificate_arn, endpoint_type, and security_policy.
        - A mutual_tls_authentication block when truststore fields are set.
        - An aws_apigatewayv2_api_mapping resource referencing the API, domain, and stage.

        Returns empty string when no custom_domain is configured.
        """
        config = self._resolve_config(instance)
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
            self._r.render_resource(
                "aws_apigatewayv2_domain_name", domain_resource_name, domain_attrs
            )
        )

        # Determine stage reference for the api_mapping
        # Use the first configured stage, or fall back to $default
        stage_resource_ref: str
        stages = getattr(config, "stages", None)
        if stages:
            first_stage_name = stages[0].get("name", "$default")
            sanitized_stage = self._sanitize_route_name(first_stage_name)
            stage_resource_ref = (
                f"aws_apigatewayv2_stage.{instance.name}_{sanitized_stage}_stage.id"
            )
        else:
            stage_resource_ref = (
                f"aws_apigatewayv2_stage.{instance.name}_default_stage.id"
            )

        # aws_apigatewayv2_api_mapping resource
        mapping_resource_name = f"{instance.name}_api_mapping"
        mapping_attrs: dict = {
            "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
            "domain_name": f"aws_apigatewayv2_domain_name.{domain_resource_name}.id",
            "stage": stage_resource_ref,
        }
        parts.append(
            self._r.render_resource(
                "aws_apigatewayv2_api_mapping", mapping_resource_name, mapping_attrs
            )
        )

        return "\n".join(parts)

    def _generate_vpc_links(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_vpc_link resources for each configured VPC link.

        Each VPC link resource includes name, subnet_ids, and security_group_ids.
        Returns empty string when no VPC links are configured.
        """
        config = self._resolve_config(instance)
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
                self._r.render_resource(
                    "aws_apigatewayv2_vpc_link", resource_name, attrs
                )
            )

        return "\n".join(parts)

    def _generate_integrations(self, instance: ResourceInstanceIR) -> str:
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
        config = self._resolve_config(instance)
        integrations = getattr(config, "integrations", None)
        if not integrations:
            return ""

        parts: list[str] = []

        for integration in integrations:
            integ_name = integration["name"]
            integ_type = integration.get("type", "HTTP_PROXY")
            resource_name = f"{instance.name}_{integ_name}_integration"

            attrs: dict = {
                "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
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
                attrs["connection_id"] = (
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
                attrs["credentials_arn"] = "var.credentials_arn"

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
                self._r.render_resource(
                    "aws_apigatewayv2_integration", resource_name, attrs
                )
            )

        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an API Gateway instance.

        Always outputs: api_id, api_endpoint, execution_arn.
        Conditionally outputs:
        - invoke_url per stage (when stages are configured)
        - domain_name and target_domain_name (when custom domain is configured)
        - authorizer_id per authorizer (when authorizers are configured)
        - vpc_link_id per VPC link (when VPC links are configured)
        """
        config = self._resolve_config(instance)
        parts = [
            self._r.render_output(
                f"{instance.name}_api_id",
                f"aws_apigatewayv2_api.{instance.name}.id",
                "ID of the API Gateway",
            ),
            self._r.render_output(
                f"{instance.name}_api_endpoint",
                f"aws_apigatewayv2_api.{instance.name}.api_endpoint",
                "Endpoint URL of the API Gateway",
            ),
            self._r.render_output(
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
                sanitized_stage = self._sanitize_route_name(stage_name)
                parts.append(
                    self._r.render_output(
                        f"{instance.name}_{sanitized_stage}_invoke_url",
                        f"aws_apigatewayv2_stage.{instance.name}_{sanitized_stage}_stage.invoke_url",
                        f"Invoke URL for the {stage_name} stage",
                    )
                )

        # Output domain_name and target_domain_name for custom domain
        custom_domain = getattr(config, "custom_domain", None)
        if custom_domain is not None:
            parts.append(
                self._r.render_output(
                    f"{instance.name}_domain_name",
                    f"aws_apigatewayv2_domain_name.{instance.name}_domain.domain_name",
                    "Custom domain name",
                )
            )
            parts.append(
                self._r.render_output(
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
                    self._r.render_output(
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
                    self._r.render_output(
                        f"{instance.name}_{vpc_link_name}_vpc_link_id",
                        f"aws_apigatewayv2_vpc_link.{instance.name}_{vpc_link_name}_vpc_link.id",
                        f"ID of the {vpc_link_name} VPC link",
                    )
                )

        return "\n".join(parts)
