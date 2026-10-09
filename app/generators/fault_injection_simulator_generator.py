from app.generators.base import get_typed_config
from app.generators.fis_ec2 import add_ec2_fault_attributes
from app.generators.fis_ecs import add_ecs_fault_attributes
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.fault_injection_simulator_config import (
    FaultInjectionSimulatorConfig,
)
from app.models.ir_models import ResourceInstanceIR


class FaultInjectionSimulatorGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, FaultInjectionSimulatorConfig)
        attrs = {
            "description": Expr("var.description"),
            "role_arn": Expr("var.role_arn"),
            "stop_condition": {"source": "none"},
            "action": {
                "name": Expr("var.action_name"),
                "action_id": Expr("var.action_id"),
            },
        }
        if config._targets_ec2:
            add_ec2_fault_attributes(attrs)
        if config._targets_ecs:
            add_ecs_fault_attributes(attrs, self._r)
        identity = 'data "aws_partition" "experiment" {}\ndata "aws_region" "experiment" {}\ndata "aws_caller_identity" "experiment" {}\n\n'
        return identity + self._r.render_resource(
            "aws_fis_experiment_template", instance.name, attrs
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
                self._r.render_output(
                    "template_arn",
                    f'format("arn:%s:fis:%s:%s:experiment-template/%s", data.aws_partition.experiment.partition, data.aws_region.experiment.region, data.aws_caller_identity.experiment.account_id, {ref}.id)',
                    "Template ARN",
                ),
            ]
        )
