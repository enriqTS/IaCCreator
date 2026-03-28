"""API Gateway service generator — produces HCL for aws_apigatewayv2_api resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class APIGatewayGenerator:
    """Generates Terraform files for API Gateway (HTTP API) resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate api-gateway.tf with aws_apigatewayv2_api resource."""
        attrs: dict = {
            "name": "var.api_name",
            "protocol_type": "var.protocol_type",
        }
        if instance.config.description is not None:
            attrs["description"] = "var.description"
        if instance.config.cors_configuration is not None:
            attrs["cors_configuration"] = "var.cors_configuration"
        if instance.config.disable_execute_api_endpoint is not None:
            attrs["disable_execute_api_endpoint"] = "var.disable_execute_api_endpoint"
        # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
        if instance.config.protocol_type == "WEBSOCKET":
            if instance.config.route_selection_expression is not None:
                attrs["route_selection_expression"] = "var.route_selection_expression"
        if instance.config.tags is not None:
            attrs["tags"] = "var.tags"

        return self._r.render_resource("aws_apigatewayv2_api", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an API Gateway instance."""
        parts = [
            self._r.render_variable("api_name", "string", "Name of the API Gateway"),
            self._r.render_variable("protocol_type", "string", "Protocol type", default="HTTP"),
        ]
        if instance.config.description is not None:
            parts.append(self._r.render_variable(
                "description", "string", "Description of the API",
                default=instance.config.description,
            ))
        if instance.config.cors_configuration is not None:
            parts.append(self._r.render_variable(
                "cors_configuration", "map(string)", "CORS configuration for the API",
            ))
        if instance.config.disable_execute_api_endpoint is not None:
            parts.append(self._r.render_variable(
                "disable_execute_api_endpoint", "bool",
                "Disable the default execute-api endpoint",
                default=instance.config.disable_execute_api_endpoint,
            ))
        # route_selection_expression — only when protocol_type is WEBSOCKET (visible_when)
        if instance.config.protocol_type == "WEBSOCKET":
            if instance.config.route_selection_expression is not None:
                parts.append(self._r.render_variable(
                    "route_selection_expression", "string",
                    "Route selection expression for WebSocket APIs",
                    default=instance.config.route_selection_expression,
                ))
        if instance.config.tags is not None:
            parts.append(self._r.render_variable(
                "tags", "map(string)", "Tags to apply to the API Gateway",
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an API Gateway instance."""
        parts = [
            self._r.render_output(
                "api_id",
                f"aws_apigatewayv2_api.{instance.name}.id",
                "ID of the API Gateway",
            ),
            self._r.render_output(
                "api_endpoint",
                f"aws_apigatewayv2_api.{instance.name}.api_endpoint",
                "Endpoint URL of the API Gateway",
            ),
        ]
        return "\n".join(parts)
