from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.security_hub_config import SecurityHubConfig
from app.models.ir_models import ResourceInstanceIR


class SecurityHubGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SecurityHubConfig)
        return self._r.render_resource(
            "aws_securityhub_account",
            instance.name,
            {
                "enable_default_standards": Expr("var.enable_default_standards"),
                "control_finding_generator": Expr("var.control_finding_generator"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SecurityHubConfig)
        fields = [
            ("enable_default_standards", "bool", "Enable default standards"),
            ("control_finding_generator", "string", "Finding generator mode"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_securityhub_account.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "security_hub_arn", f"{ref}.arn", "Security Hub ARN"
                ),
            ]
        )
