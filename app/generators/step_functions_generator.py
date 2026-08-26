"""Terraform generator for AWS Step Functions state machines."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.step_functions_config import StepFunctionsConfig
from app.models.ir_models import ResourceInstanceIR


class StepFunctionsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, StepFunctionsConfig)
        return self._r.render_resource(
            "aws_sfn_state_machine",
            instance.name,
            {
                "name": instance.name,
                "role_arn": Expr("var.role_arn"),
                "definition": Expr("var.definition"),
                "type": Expr("var.state_machine_type"),
                "publish": Expr("var.publish"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, StepFunctionsConfig)
        fields = [
            ("role_arn", "string", "IAM execution role ARN"),
            ("definition", "string", "Amazon States Language definition"),
            ("state_machine_type", "string", "Workflow execution type"),
            ("publish", "bool", "Publish state machine versions"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_sfn_state_machine.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "state_machine_arn", f"{ref}.arn", "State machine ARN"
                ),
                self._r.render_output(
                    "state_machine_id", f"{ref}.id", "State machine ID"
                ),
            ]
        )
