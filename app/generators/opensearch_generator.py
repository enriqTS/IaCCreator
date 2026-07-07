"""OpenSearch service generator — produces HCL for aws_opensearch_domain resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class OpenSearchGenerator:
    """Generates Terraform files for OpenSearch domains."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_opensearch_domain resource."""
        attrs: dict = {"domain_name": "var.domain_name"}

        return self._r.render_resource("aws_opensearch_domain", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an OpenSearch domain."""
        parts = [
            self._r.render_variable(
                "domain_name", "string", "Name of the OpenSearch domain"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an OpenSearch domain."""
        parts = [
            self._r.render_output(
                "domain_arn",
                f"aws_opensearch_domain.{instance.name}.arn",
                "ARN of the OpenSearch domain",
            ),
            self._r.render_output(
                "domain_endpoint",
                f"aws_opensearch_domain.{instance.name}.endpoint",
                "Endpoint of the OpenSearch domain",
            ),
        ]
        return "\n".join(parts)
