"""Workflow-owned ECS Fargate tasks and scoped execution-role grants."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_ecs import ecs_workflow_locals
from app.models.connection_configs.workflows import (
    StepFunctionsEcsConfig,
    StepFunctionsLambdaConfig,
    StepFunctionsSecretConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.models.workflow_states import placeholder_errors
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.ecs_task_target import prepare_fargate_target


class StepFunctionsEcsHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The workflow waits for the Fargate task to stop. Configure task networking, container behavior, retries, and monitoring separately.",
            )
        ]

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        workflow = connection.source_name
        peers = [
            item
            for item in project.connections
            if item.source_name == workflow
            and item.target_service == ServiceType.ECS
            and item.connection_type == "runs_task"
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
                        "msg": "Workflow ECS tasks require an execution role ARN",
                    }
                ],
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsEcsConfig.model_validate(item.connection_config)
            if config.state_name in bindings and bindings[config.state_name] != (
                item.target_name,
                config.task_count,
            ):
                raise InvalidConnectionConfigError(
                    workflow,
                    item.target_name,
                    item.connection_type,
                    [
                        {
                            "loc": ("state_name",),
                            "msg": "Conflicting ECS tasks cannot replace the same workflow state",
                        }
                    ],
                )
            bindings[config.state_name] = (item.target_name, config.task_count)
            prepare_fargate_target(
                item, project, self._find_instance(item.target_name, project)
            )
        secrets = [
            item
            for item in project.connections
            if item.source_name == workflow
            and item.target_service == ServiceType.SECRETS_MANAGER
            and item.connection_type == "reads_secret"
        ]
        lambdas = [
            item
            for item in project.connections
            if item.source_name == workflow
            and item.target_service == ServiceType.LAMBDA
            and item.connection_type == "invokes"
        ]
        occupied = {
            StepFunctionsSecretConfig.model_validate(item.connection_config).state_name
            for item in secrets
        } | {
            StepFunctionsLambdaConfig.model_validate(item.connection_config).state_name
            for item in lambdas
        }
        if overlap := set(bindings) & occupied:
            raise InvalidConnectionConfigError(
                workflow,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("state_name",),
                        "msg": f"Workflow state {sorted(overlap)[0]!r} belongs to multiple task connections",
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
        instance.config._runs_ecs_tasks = True
        targets = sorted({target for target, _ in bindings.values()})
        result = ConnectionContribution()
        fields = (
            ("cluster_arn", "cluster_arn", "string"),
            ("task_definition_arn", "task_definition_arn", "string"),
            ("task_role_arn", "task_role_arn", "string"),
            ("subnet_ids", "subnet_ids", "list(string)"),
            ("security_group_ids", "security_group_ids", "list(string)"),
            ("assign_public_ip", "assign_public_ip", "bool"),
        )
        for index, target in enumerate(targets):
            for suffix, output, kind in fields:
                result.inputs.append(
                    ModuleInput(
                        module=workflow,
                        name=f"workflow_ecs_{index}_{suffix}",
                        value=f"module.{target}.{output}",
                        type=kind,
                    )
                )
        task_bindings = {}
        for state, (target, count) in sorted(bindings.items()):
            prefix = f"var.workflow_ecs_{targets.index(target)}"
            task_bindings[state] = {
                "cluster": Expr(f"{prefix}_cluster_arn"),
                "definition": Expr(f"{prefix}_task_definition_arn"),
                "task_role": Expr(f"{prefix}_task_role_arn"),
                "subnets": Expr(f"{prefix}_subnet_ids"),
                "security_groups": Expr(f"{prefix}_security_group_ids"),
                "assign_public_ip": Expr(f"{prefix}_assign_public_ip"),
                "count": count,
            }
        result.resources.append(
            self._resource(
                workflow,
                "ecs_tasks.tf",
                ecs_workflow_locals(task_bindings, bool(lambdas), bool(secrets)),
            )
        )
        result.resources.append(
            self._resource(
                workflow,
                "ecs_tasks_policy.tf",
                self._policy(workflow, len(targets)),
            )
        )
        return result

    def _policy(self, workflow: str, target_count: int) -> str:
        render = self._renderer.render_resource
        statements = [
            {
                "Effect": "Allow",
                "Action": ["ecs:RunTask"],
                "Resource": [
                    Expr(f"var.workflow_ecs_{index}_task_definition_arn")
                    for index in range(target_count)
                ],
                "Condition": {
                    "ArnEquals": {
                        "ecs:cluster": [
                            Expr(f"var.workflow_ecs_{index}_cluster_arn")
                            for index in range(target_count)
                        ]
                    }
                },
            },
            {
                "Effect": "Allow",
                "Action": ["ecs:DescribeTasks", "ecs:StopTask"],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "events:PutRule",
                    "events:PutTargets",
                    "events:DescribeRule",
                ],
                "Resource": [
                    Expr(
                        'format("arn:%s:events:%s:%s:rule/StepFunctionsGetEventsForECSTaskRule", '
                        "data.aws_partition.ecs_tasks_policy.partition, "
                        "data.aws_region.ecs_tasks_policy.name, "
                        "data.aws_caller_identity.ecs_tasks_policy.account_id)"
                    )
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": [
                    Expr(f"var.workflow_ecs_{index}_task_role_arn")
                    for index in range(target_count)
                ],
                "Condition": {
                    "StringEquals": {"iam:PassedToService": "ecs-tasks.amazonaws.com"}
                },
            },
        ]
        return (
            'data "aws_partition" "ecs_tasks_policy" {}\n'
            'data "aws_region" "ecs_tasks_policy" {}\n'
            'data "aws_caller_identity" "ecs_tasks_policy" {}\n'
            + render(
                "aws_iam_role_policy",
                "ecs_tasks",
                {
                    "name": f"{workflow}-ecs-tasks",
                    "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                    "policy": self._renderer.render_json_policy(
                        {"Version": "2012-10-17", "Statement": statements}
                    ),
                },
            )
        )
