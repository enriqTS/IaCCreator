"""SageMaker service generator — produces HCL for aws_sagemaker_notebook_instance resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.generators.variable_schemas import VARIABLE_SCHEMAS
from app.models.input_models import ServiceType
from app.models.ir_models import ResourceInstanceIR


class SageMakerGenerator:
    """Generates Terraform files for SageMaker notebook instances."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_sagemaker_notebook_instance resource."""
        attrs: dict = {
            "name": "var.notebook_instance_name",
            "instance_type": "var.instance_type",
            "role_arn": "var.role_arn",
            "volume_size": "var.volume_size",
            "direct_internet_access": "var.direct_internet_access",
            "root_access": "var.root_access",
            "tags": "var.tags",
        }
        return self._r.render_resource("aws_sagemaker_notebook_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf dynamically from VARIABLE_SCHEMAS."""
        schema = VARIABLE_SCHEMAS[ServiceType.SAGEMAKER]
        parts = []
        for entry in schema:
            tf_type = "map(string)" if entry.type == "map" else entry.type
            parts.append(self._r.render_variable(entry.name, tf_type, entry.description, entry.default))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a SageMaker notebook instance."""
        parts = [
            self._r.render_output(
                "notebook_instance_arn",
                f"aws_sagemaker_notebook_instance.{instance.name}.arn",
                "ARN of the SageMaker notebook instance",
            ),
            self._r.render_output(
                "notebook_instance_name",
                f"aws_sagemaker_notebook_instance.{instance.name}.name",
                "Name of the SageMaker notebook instance",
            ),
        ]
        return "\n".join(parts)
