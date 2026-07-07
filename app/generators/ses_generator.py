"""SES service generator — produces HCL for aws_ses_domain_identity resources."""

from app.generators.hcl_renderer import HCLRenderer
from app.models.ir_models import ResourceInstanceIR


class SESGenerator:
    """Generates Terraform files for SES domain identities."""

    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate resource.tf with aws_ses_domain_identity resource."""
        attrs: dict = {"domain": "var.domain"}

        return self._r.render_resource("aws_ses_domain_identity", instance.name, attrs)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate variables.tf for an SES domain identity."""
        parts = [
            self._r.render_variable(
                "domain", "string", "Domain for the SES domain identity"
            ),
        ]
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        """Generate outputs.tf for an SES domain identity."""
        parts = [
            self._r.render_output(
                "domain_arn",
                f"aws_ses_domain_identity.{instance.name}.arn",
                "ARN of the SES domain identity",
            ),
            self._r.render_output(
                "verification_token",
                f"aws_ses_domain_identity.{instance.name}.verification_token",
                "Verification token for the SES domain identity",
            ),
        ]
        return "\n".join(parts)
