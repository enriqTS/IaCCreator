"""EC2 Image Builder service generator — produces HCL for aws_imagebuilder_image_pipeline resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class EC2ImageBuilderGenerator:
    """Generates Terraform files for EC2 Image Builder pipelines."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_imagebuilder_image_pipeline resource."""
        attrs: dict = {
            "name": "var.pipeline_name",
            "image_recipe_arn": "var.image_recipe_arn",
            "infrastructure_configuration_arn": "var.infrastructure_configuration_arn",
        }

        return self._r.render_resource(
            "aws_imagebuilder_image_pipeline", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an EC2 Image Builder pipeline."""
        parts = [
            self._r.render_variable(
                "pipeline_name", "string", "Name of the Image Builder pipeline"
            ),
            self._r.render_variable(
                "image_recipe_arn", "string", "ARN of the image recipe"
            ),
            self._r.render_variable(
                "infrastructure_configuration_arn",
                "string",
                "ARN of the infrastructure configuration",
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an EC2 Image Builder pipeline."""
        parts = [
            self._r.render_output(
                "pipeline_arn",
                f"aws_imagebuilder_image_pipeline.{instance.name}.arn",
                "ARN of the Image Builder pipeline",
            ),
        ]
        return "\n".join(parts)
