"""IAM service generator — produces HCL for IAM role and policy resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class IAMGenerator:
    """Generates Terraform files for standalone IAM role and policy resources."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate iam.tf with aws_iam_role and aws_iam_role_policy resources."""
        role_attrs = {
            "name": "var.role_name",
            "assume_role_policy": "var.assume_role_policy",
        }
        role_block = self._r.render_resource("aws_iam_role", instance.name, role_attrs)

        policy_attrs = {
            "name": "var.policy_name",
            "role": f"aws_iam_role.{instance.name}.id",
            "policy": "var.policy_document",
        }
        policy_block = self._r.render_resource(
            "aws_iam_role_policy", f"{instance.name}_policy", policy_attrs
        )

        return role_block + "\n" + policy_block

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an IAM instance."""
        parts = [
            self._r.render_variable("role_name", "string", "Name of the IAM role"),
            self._r.render_variable(
                "assume_role_policy", "string", "Assume role policy JSON document"
            ),
            self._r.render_variable("policy_name", "string", "Name of the IAM policy"),
            self._r.render_variable(
                "policy_document", "string", "IAM policy JSON document"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an IAM instance."""
        parts = [
            self._r.render_output(
                "role_arn",
                f"aws_iam_role.{instance.name}.arn",
                "ARN of the IAM role",
            ),
            self._r.render_output(
                "role_name",
                f"aws_iam_role.{instance.name}.name",
                "Name of the IAM role",
            ),
        ]
        return "\n".join(parts)
