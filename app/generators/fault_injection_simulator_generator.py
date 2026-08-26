from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.fault_injection_simulator_config import (
    FaultInjectionSimulatorConfig,
)
from app.models.ir_models import ResourceInstanceIR


class FaultInjectionSimulatorGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, FaultInjectionSimulatorConfig)
        return self._r.render_resource(
            "aws_fis_experiment_template",
            instance.name,
            {
                "description": Expr("var.description"),
                "role_arn": Expr("var.role_arn"),
                "stop_condition": {"source": "none"},
                "action": {
                    "name": Expr("var.action_name"),
                    "action_id": Expr("var.action_id"),
                },
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, FaultInjectionSimulatorConfig)
        fields = [
            ("description", "string", "Experiment description"),
            ("role_arn", "string", "Experiment IAM role ARN"),
            ("action_name", "string", "Action identifier"),
            ("action_id", "string", "AWS FIS action ID"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_fis_experiment_template.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("template_id", f"{ref}.id", "Template ID"),
                self._r.render_output("template_arn", f"{ref}.arn", "Template ARN"),
            ]
        )
