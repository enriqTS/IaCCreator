"""ECR service generator — produces HCL for aws_ecr_repository resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class ECRGenerator:
    """Generates Terraform files for ECR repositories."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_ecr_repository resource."""
        attrs: dict = {"name": "var.repository_name"}
        if instance.config.ecr_image_tag_mutability is not None:
            attrs["image_tag_mutability"] = "var.ecr_image_tag_mutability"
        if instance.config.ecr_scan_on_push is not None:
            attrs["image_scanning_configuration"] = {"scan_on_push": "var.ecr_scan_on_push"}

        return self._r.render_resource("aws_ecr_repository", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an ECR repository."""
        parts = [
            self._r.render_variable("repository_name", "string", "Name of the ECR repository"),
        ]
        if instance.config.ecr_image_tag_mutability is not None:
            parts.append(self._r.render_variable(
                "ecr_image_tag_mutability", "string", "Image tag mutability setting (MUTABLE or IMMUTABLE)",
                default=instance.config.ecr_image_tag_mutability,
            ))
        if instance.config.ecr_scan_on_push is not None:
            parts.append(self._r.render_variable(
                "ecr_scan_on_push", "bool", "Whether to scan images on push",
                default=instance.config.ecr_scan_on_push,
            ))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an ECR repository."""
        parts = [
            self._r.render_output(
                "repository_arn",
                f"aws_ecr_repository.{instance.name}.arn",
                "ARN of the ECR repository",
            ),
            self._r.render_output(
                "repository_url",
                f"aws_ecr_repository.{instance.name}.repository_url",
                "URL of the ECR repository",
            ),
        ]
        return "\n".join(parts)
