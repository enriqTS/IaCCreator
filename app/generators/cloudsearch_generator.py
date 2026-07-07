"""CloudSearch service generator — produces HCL for aws_cloudsearch_domain resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class CloudSearchGenerator:
    """Generates Terraform files for CloudSearch domains."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_cloudsearch_domain resource."""
        attrs: dict = {"name": "var.domain_name"}

        return self._r.render_resource("aws_cloudsearch_domain", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CloudSearch domain."""
        parts = [
            self._r.render_variable(
                "domain_name", "string", "Name of the CloudSearch domain"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CloudSearch domain."""
        parts = [
            self._r.render_output(
                "domain_arn",
                f"aws_cloudsearch_domain.{instance.name}.arn",
                "ARN of the CloudSearch domain",
            ),
            self._r.render_output(
                "domain_id",
                f"aws_cloudsearch_domain.{instance.name}.id",
                "ID of the CloudSearch domain",
            ),
        ]
        return "\n".join(parts)
