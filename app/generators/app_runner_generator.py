"""App Runner service generator — produces HCL for aws_apprunner_service resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class AppRunnerGenerator:
    """Generates Terraform files for App Runner services."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_apprunner_service resource."""
        attrs: dict = {
            "service_name": "var.service_name",
            "source_configuration": {
                "image_repository": {
                    "image_identifier": "var.image_identifier",
                    "image_repository_type": "ECR",
                },
            },
        }

        return self._r.render_resource("aws_apprunner_service", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an App Runner service."""
        parts = [
            self._r.render_variable("service_name", "string", "Name of the App Runner service"),
            self._r.render_variable("image_identifier", "string", "Container image identifier for the App Runner service"),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an App Runner service."""
        parts = [
            self._r.render_output(
                "service_arn",
                f"aws_apprunner_service.{instance.name}.arn",
                "ARN of the App Runner service",
            ),
            self._r.render_output(
                "service_url",
                f"aws_apprunner_service.{instance.name}.service_url",
                "URL of the App Runner service",
            ),
        ]
        return "\n".join(parts)
