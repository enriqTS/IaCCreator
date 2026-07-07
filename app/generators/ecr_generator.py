"""ECR service generator — produces HCL for aws_ecr_repository resources."""

from app.generators.base import get_typed_config  # noqa: F401
from app.generators.hcl_renderer import HCLRenderer
from app.models.input_models.ecr_config import EcrConfig
from app.models.ir_models import ResourceInstanceIR


def _resolve_config(instance: ResourceInstanceIR) -> EcrConfig:
    """Resolve typed EcrConfig, falling back to instance.config during migration."""
    if isinstance(instance.config, EcrConfig):
        return instance.config
    return instance.config  # type: ignore[return-value]


class ECRGenerator:
    """Generates Terraform files for ECR repositories."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_ecr_repository resource."""
        config = _resolve_config(instance)

        attrs: dict = {"name": "var.repository_name"}
        if config.ecr_image_tag_mutability is not None:
            attrs["image_tag_mutability"] = "var.ecr_image_tag_mutability"
        if config.ecr_scan_on_push is not None:
            attrs["image_scanning_configuration"] = {
                "scan_on_push": "var.ecr_scan_on_push"
            }

        return self._r.render_resource("aws_ecr_repository", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an ECR repository."""
        config = _resolve_config(instance)

        parts = [
            self._r.render_variable(
                "repository_name", "string", "Name of the ECR repository"
            ),
        ]
        if config.ecr_image_tag_mutability is not None:
            parts.append(
                self._r.render_variable(
                    "ecr_image_tag_mutability",
                    "string",
                    "Image tag mutability setting (MUTABLE or IMMUTABLE)",
                    default=config.ecr_image_tag_mutability,
                )
            )
        if config.ecr_scan_on_push is not None:
            parts.append(
                self._r.render_variable(
                    "ecr_scan_on_push",
                    "bool",
                    "Whether to scan images on push",
                    default=config.ecr_scan_on_push,
                )
            )
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
