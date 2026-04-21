"""Neptune service generator — produces HCL for aws_neptune_cluster resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class NeptuneGenerator:
    """Generates Terraform files for Neptune clusters."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_neptune_cluster resource."""
        attrs: dict = {"cluster_identifier": "var.cluster_identifier"}

        return self._r.render_resource("aws_neptune_cluster", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a Neptune cluster."""
        parts = [
            self._r.render_variable("cluster_identifier", "string", "Identifier for the Neptune cluster"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a Neptune cluster."""
        parts = [
            self._r.render_output(
                "cluster_arn",
                f"aws_neptune_cluster.{instance.name}.arn",
                "ARN of the Neptune cluster",
            ),
            self._r.render_output(
                "cluster_endpoint",
                f"aws_neptune_cluster.{instance.name}.endpoint",
                "Endpoint of the Neptune cluster",
            ),
        ]
        return "\n".join(parts)
