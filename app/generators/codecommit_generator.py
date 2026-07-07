"""CodeCommit service generator — produces HCL for aws_codecommit_repository resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class CodeCommitGenerator:
    """Generates Terraform files for CodeCommit repositories."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_codecommit_repository resource."""
        attrs: dict = {"repository_name": "var.repository_name"}

        return self._r.render_resource(
            "aws_codecommit_repository", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for a CodeCommit repository."""
        parts = [
            self._r.render_variable(
                "repository_name", "string", "Name of the CodeCommit repository"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for a CodeCommit repository."""
        parts = [
            self._r.render_output(
                "repository_arn",
                f"aws_codecommit_repository.{instance.name}.arn",
                "ARN of the CodeCommit repository",
            ),
            self._r.render_output(
                "clone_url_http",
                f"aws_codecommit_repository.{instance.name}.clone_url_http",
                "HTTP clone URL of the CodeCommit repository",
            ),
        ]
        return "\n".join(parts)
