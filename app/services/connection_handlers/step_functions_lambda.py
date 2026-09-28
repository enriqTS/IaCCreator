"""Workflow-owned Lambda tasks and scoped invoke grants."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_lambda import lambda_workflow_locals
from app.models.connection_configs.workflows import (
    StepFunctionsLambdaConfig,
    StepFunctionsSecretConfig,
)
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.models.workflow_states import placeholder_errors
from app.services.connection_handlers.base import BaseConnectionHandler


class StepFunctionsLambdaHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        workflow = connection.source_name
        peers = [
            item
            for item in project.connections
            if item.source_name == workflow
            and item.target_service == ServiceType.LAMBDA
            and item.connection_type == "invokes"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(workflow, project)
        if not instance.config.role_arn:
            raise InvalidConnectionConfigError(
                workflow,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("role_arn",),
                        "msg": "Workflow Lambda tasks require an execution role ARN",
                    }
                ],
            )
        bindings = {}
        for item in peers:
            state = StepFunctionsLambdaConfig.model_validate(
                item.connection_config
            ).state_name
            if state in bindings and bindings[state] != item.target_name:
                raise InvalidConnectionConfigError(
                    workflow,
                    item.target_name,
                    item.connection_type,
                    [
                        {
                            "loc": ("state_name",),
                            "msg": "Two functions cannot replace the same workflow state",
                        }
                    ],
                )
            bindings[state] = item.target_name
        secrets = [
            item
            for item in project.connections
            if item.source_name == workflow
            and item.target_service == ServiceType.SECRETS_MANAGER
            and item.connection_type == "reads_secret"
        ]
        secret_states = {
            StepFunctionsSecretConfig.model_validate(item.connection_config).state_name
            for item in secrets
        }
        if overlap := set(bindings) & secret_states:
            raise InvalidConnectionConfigError(
                workflow,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("state_name",),
                        "msg": f"Workflow state {sorted(overlap)[0]!r} belongs to both Lambda and Secrets Manager",
                    }
                ],
            )
        errors = placeholder_errors(instance.config.definition, set(bindings))
        if errors:
            raise InvalidConnectionConfigError(
                workflow,
                connection.target_name,
                connection.connection_type,
                [{"loc": ("definition",), "msg": error} for error in errors],
            )
        instance.config._invokes_lambdas = True
        functions = sorted(set(bindings.values()))
        result = ConnectionContribution()
        for index, name in enumerate(functions):
            result.inputs.append(
                self._input(
                    workflow,
                    "workflow",
                    f"lambda_{index}_arn",
                    f"module.{name}.function_arn",
                    "Lambda function invoked by the workflow",
                )
            )
        variables = {
            name: Expr(f"var.workflow_lambda_{functions.index(target)}_arn")
            for name, target in sorted(bindings.items())
        }
        result.resources.append(
            self._resource(
                workflow,
                "lambda_tasks.tf",
                lambda_workflow_locals(variables, bool(secrets)),
            )
        )
        result.resources.append(
            self._resource(
                workflow,
                "lambda_tasks_policy.tf",
                self._renderer.render_resource(
                    "aws_iam_role_policy",
                    "lambda_tasks",
                    {
                        "name": f"{workflow}-lambda-tasks",
                        "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                        "policy": self._renderer.render_json_policy(
                            {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": ["lambda:InvokeFunction"],
                                        "Resource": [
                                            Expr(f"var.workflow_lambda_{index}_arn")
                                            for index in range(len(functions))
                                        ],
                                    }
                                ],
                            }
                        ),
                    },
                ),
            )
        )
        return result
