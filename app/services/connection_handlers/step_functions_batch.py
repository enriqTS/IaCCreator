"""Workflow-owned Batch jobs and scoped submit permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_batch import batch_workflow_locals
from app.models.connection_configs.workflows import (
    StepFunctionsBatchConfig,
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
from app.services.connection_handlers.batch_task_target import prepare_batch_target


class StepFunctionsBatchHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The workflow waits for the Batch job to finish. Supply capacity to the unmanaged compute environment and configure job monitoring separately.",
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
            and item.target_service == ServiceType.BATCH
            and item.connection_type == "submits_job"
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
                        "msg": "Workflow Batch tasks require an execution role ARN",
                    }
                ],
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsBatchConfig.model_validate(item.connection_config)
            binding = (
                item.target_name,
                config.job_definition_name,
                config.job_name,
                config.array_size,
                config.job_attempts,
            )
            if config.state_name in bindings and bindings[config.state_name] != binding:
                raise InvalidConnectionConfigError(
                    workflow,
                    item.target_name,
                    item.connection_type,
                    [
                        {
                            "loc": ("state_name",),
                            "msg": "Conflicting Batch jobs cannot replace the same workflow state",
                        }
                    ],
                )
            bindings[config.state_name] = binding
            prepare_batch_target(
                item,
                project,
                self._find_instance(item.target_name, project),
                config.job_definition_name,
            )
        related = [
            (ServiceType.SECRETS_MANAGER, "reads_secret", StepFunctionsSecretConfig),
            (ServiceType.LAMBDA, "invokes", StepFunctionsLambdaConfig),
            (ServiceType.ECS, "runs_task", StepFunctionsEcsConfig),
        ]
        occupied = set()
        present = {}
        for service, kind, model in related:
            peers_of_kind = [
                item
                for item in project.connections
                if item.source_name == workflow
                and item.target_service == service
                and item.connection_type == kind
            ]
            present[service] = bool(peers_of_kind)
            occupied.update(
                model.model_validate(item.connection_config).state_name
                for item in peers_of_kind
            )
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
        instance.config._submits_batch_jobs = True
        queues = sorted({binding[0] for binding in bindings.values()})
        definitions = sorted({binding[1] for binding in bindings.values()})
        result = ConnectionContribution()
        for index, name in enumerate(queues):
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=f"workflow_batch_queue_{index}_arn",
                    value=f"module.{name}.job_queue_arn",
                )
            )
        for index, name in enumerate(definitions):
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=f"workflow_batch_definition_{index}_arn",
                    value=f"module.{name}.job_definition_arn",
                )
            )
        task_bindings = {}
        for state, (queue, definition, job_name, array_size, attempts) in sorted(
            bindings.items()
        ):
            parameters = {
                "JobName": job_name,
                "JobQueue": Expr(f"var.workflow_batch_queue_{queues.index(queue)}_arn"),
                "JobDefinition": Expr(
                    f"var.workflow_batch_definition_{definitions.index(definition)}_arn"
                ),
            }
            if array_size is not None:
                parameters["ArrayProperties"] = {"Size": array_size}
            if attempts is not None:
                parameters["RetryStrategy"] = {"Attempts": attempts}
            task_bindings[state] = parameters
        result.resources.append(
            self._resource(
                workflow,
                "batch_tasks.tf",
                batch_workflow_locals(
                    task_bindings,
                    present[ServiceType.ECS],
                    present[ServiceType.LAMBDA],
                    present[ServiceType.SECRETS_MANAGER],
                ),
            )
        )
        result.resources.append(
            self._resource(
                workflow,
                "batch_tasks_policy.tf",
                self._policy(workflow, len(queues), len(definitions)),
            )
        )
        return result

    def _policy(self, workflow: str, queue_count: int, definition_count: int) -> str:
        statements = [
            {
                "Effect": "Allow",
                "Action": ["batch:SubmitJob"],
                "Resource": [
                    *(
                        Expr(f"var.workflow_batch_queue_{index}_arn")
                        for index in range(queue_count)
                    ),
                    *(
                        Expr(f"var.workflow_batch_definition_{index}_arn")
                        for index in range(definition_count)
                    ),
                ],
            },
            {
                "Effect": "Allow",
                "Action": ["batch:DescribeJobs", "batch:TerminateJob"],
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
                        'format("arn:%s:events:%s:%s:rule/StepFunctionsGetEventsForBatchJobsRule", '
                        "data.aws_partition.batch_tasks_policy.partition, "
                        "data.aws_region.batch_tasks_policy.name, "
                        "data.aws_caller_identity.batch_tasks_policy.account_id)"
                    )
                ],
            },
        ]
        return (
            'data "aws_partition" "batch_tasks_policy" {}\n'
            'data "aws_region" "batch_tasks_policy" {}\n'
            'data "aws_caller_identity" "batch_tasks_policy" {}\n'
            + self._renderer.render_resource(
                "aws_iam_role_policy",
                "batch_tasks",
                {
                    "name": f"{workflow}-batch-tasks",
                    "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                    "policy": self._renderer.render_json_policy(
                        {"Version": "2012-10-17", "Statement": statements}
                    ),
                },
            )
        )
