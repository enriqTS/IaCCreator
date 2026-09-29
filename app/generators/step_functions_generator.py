"""Terraform generator for AWS Step Functions state machines."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.step_functions_batch import batch_workflow_attributes
from app.generators.step_functions_dynamodb import dynamodb_workflow_attributes
from app.generators.step_functions_ecs import ecs_workflow_attributes
from app.generators.step_functions_lambda import lambda_workflow_attributes
from app.generators.step_functions_secrets import secret_workflow_attributes
from app.generators.step_functions_sns import sns_workflow_attributes
from app.generators.step_functions_sqs import sqs_workflow_attributes
from app.models.input_models.step_functions_config import StepFunctionsConfig
from app.models.ir_models import ResourceInstanceIR


class StepFunctionsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, StepFunctionsConfig)
        attrs = {
            "name": instance.name,
            "role_arn": Expr("var.role_arn"),
            "definition": Expr("var.definition"),
            "type": Expr("var.state_machine_type"),
            "publish": Expr("var.publish"),
        }
        if config._uses_dynamodb_items:
            attrs.update(
                dynamodb_workflow_attributes(
                    config._sends_sqs_messages,
                    config._publishes_sns_messages,
                    config._submits_batch_jobs,
                    config._runs_ecs_tasks,
                    config._invokes_lambdas,
                    config._reads_runtime_secrets,
                )
            )
        elif config._sends_sqs_messages:
            attrs.update(
                sqs_workflow_attributes(
                    config._publishes_sns_messages,
                    config._submits_batch_jobs,
                    config._runs_ecs_tasks,
                    config._invokes_lambdas,
                    config._reads_runtime_secrets,
                )
            )
        elif config._publishes_sns_messages:
            attrs.update(
                sns_workflow_attributes(
                    config._submits_batch_jobs,
                    config._runs_ecs_tasks,
                    config._invokes_lambdas,
                    config._reads_runtime_secrets,
                )
            )
        elif config._submits_batch_jobs:
            attrs.update(
                batch_workflow_attributes(
                    config._runs_ecs_tasks,
                    config._invokes_lambdas,
                    config._reads_runtime_secrets,
                )
            )
        elif config._runs_ecs_tasks:
            attrs.update(
                ecs_workflow_attributes(
                    config._invokes_lambdas, config._reads_runtime_secrets
                )
            )
        elif config._invokes_lambdas:
            attrs.update(lambda_workflow_attributes(config._reads_runtime_secrets))
        elif config._reads_runtime_secrets:
            attrs.update(secret_workflow_attributes())
        return self._r.render_resource("aws_sfn_state_machine", instance.name, attrs)

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
