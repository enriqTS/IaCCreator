"""API Gateway service generator — produces HCL for aws_apigatewayv2_api resources."""

from app.generators.api_gateway_validator import APIGatewayValidator
from app.generators.base import get_typed_config
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
        Falls back to duck-typed access on ResourceConfig during migration
        (both models share field names for scalar API Gateway fields).
        """
        try:
            return get_typed_config(instance, ApiGatewayConfig)
        except Exception:
            # During migration, config may still be a ResourceConfig.
            # Field names are shared for scalar fields, so duck-typed access works.
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
            self._generate_api_key(instance),
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

        return self._r.render_resource("aws_apigatewayv2_api", instance.name, attrs)

    def _generate_api_key(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_api_key resource when api_key_required is true."""
        config = self._resolve_config(instance)
        if not config.api_key_required:
            return ""

        attrs: dict = {
            "api_id": f"aws_apigatewayv2_api.{instance.name}.id",
            "name": f"{instance.name}-api-key",
        }
        return self._r.render_resource(
            "aws_apigatewayv2_api_key", f"{instance.name}_api_key", attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an API Gateway instance."""
        config = self._resolve_config(instance)
        parts = [
            self._r.render_variable("api_name", "string", "Name of the API Gateway"),
            self._r.render_variable(
                "protocol_type", "string", "Protocol type", default="HTTP"
            ),
        ]
        if config.description is not None:
            parts.append(
                self._r.render_variable(
                    "description",
                    "string",
                    "Description of the API",
                    default=config.description,
                )
            )
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
        if config.tags is not None:
            parts.append(
                self._r.render_variable(
                    "tags",
                    "map(string)",
                    "Tags to apply to the API Gateway",
                )
            )
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

                # API key required
                if config.api_key_required:
                    attrs["api_key_required"] = True

                parts.append(
                    self._r.render_resource(
                        "aws_apigatewayv2_route", resource_name, attrs
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

                # API key required
                if config.api_key_required:
                    attrs["api_key_required"] = True

                parts.append(
                    self._r.render_resource(
                        "aws_apigatewayv2_route", resource_name, attrs
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

                    # API key required
                    if config.api_key_required:
                        attrs["api_key_required"] = True

                    parts.append(
                        self._r.render_resource(
                            "aws_apigatewayv2_route", resource_name, attrs
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

    def _generate_stages(self, instance: ResourceInstanceIR) -> str:
        """Generate aws_apigatewayv2_stage resources and associated CloudWatch log groups.

        For each configured stage, produces:
        - An aws_apigatewayv2_stage resource with auto_deploy, stage_variables,
          default_route_settings (throttling), route_settings (per-route throttling),
          and access_log_settings when logging is enabled.
        - An aws_cloudwatch_log_group resource when access logging is enabled.

        When no stages are configured, generates a single $default stage with auto_deploy=true.
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

            # default_route_settings block (throttling)
            throttling_burst = stage_cfg.get("throttling_burst_limit")
            throttling_rate = stage_cfg.get("throttling_rate_limit")
            if throttling_burst is not None or throttling_rate is not None:
                default_route_settings: dict = {}
                if throttling_burst is not None:
                    default_route_settings["throttling_burst_limit"] = throttling_burst
                if throttling_rate is not None:
                    default_route_settings["throttling_rate_limit"] = throttling_rate
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

            # access_log_settings block
            access_logging_enabled = stage_cfg.get("access_logging_enabled", False)
            if access_logging_enabled:
                log_group_resource_name = f"{instance.name}_{sanitized_name}_log_group"
                log_format = stage_cfg.get("access_log_format") or default_log_format

                attrs["access_log_settings"] = {
                    "destination_arn": f"aws_cloudwatch_log_group.{log_group_resource_name}.arn",
                    "format": log_format,
                }

            parts.append(
                self._r.render_resource("aws_apigatewayv2_stage", resource_name, attrs)
            )

            # Generate CloudWatch log group when access logging is enabled
            if access_logging_enabled:
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
          containing certificate_arn, endpoint_type REGIONAL, and security_policy TLS_1_2.
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

        # aws_apigatewayv2_domain_name resource
        domain_resource_name = f"{instance.name}_domain"
        domain_attrs: dict = {
            "domain_name": domain_name,
            "domain_name_configuration": {
                "certificate_arn": certificate_arn,
                "endpoint_type": "REGIONAL",
                "security_policy": "TLS_1_2",
            },
        }
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
