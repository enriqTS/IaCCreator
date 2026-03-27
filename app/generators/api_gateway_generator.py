"""API Gateway service generator — produces HCL for aws_apigatewayv2_api resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class APIGatewayGenerator:
    """Generates Terraform files for API Gateway (HTTP API) resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate api-gateway.tf with aws_apigatewayv2_api resource."""
        attrs = {
            "name": "var.api_name",
            "protocol_type": "var.protocol_type",
        }
        return self._r.render_resource("aws_apigatewayv2_api", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an API Gateway instance."""
        parts = [
            self._r.render_variable("api_name", "string", "Name of the API Gateway"),
            self._r.render_variable("protocol_type", "string", "Protocol type", default="HTTP"),
        ]
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
