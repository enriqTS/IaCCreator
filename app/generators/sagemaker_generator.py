"""SageMaker service generator — produces HCL for aws_sagemaker_notebook_instance resources."""

from app.generators.hcl_renderer import HCLRenderer
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
        }
        return self._r.render_resource("aws_sagemaker_notebook_instance", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a SageMaker notebook instance."""
        parts = [
            self._r.render_variable("notebook_instance_name", "string", "Name of the SageMaker notebook instance"),
            self._r.render_variable("instance_type", "string", "Instance type for the notebook instance"),
            self._r.render_variable("role_arn", "string", "IAM role ARN for the notebook instance"),
        ]
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
