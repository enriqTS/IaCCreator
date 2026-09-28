"""Workflow-owned SQS SendMessage tasks and queue-scoped permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_sqs import sqs_workflow_locals
from app.models.connection_configs.workflows import (
    StepFunctionsBatchConfig,
    StepFunctionsEcsConfig,
    StepFunctionsLambdaConfig,
    StepFunctionsSecretConfig,
    StepFunctionsSnsConfig,
    StepFunctionsSqsConfig,
)
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
    ResourceInstanceIR,
)
from app.models.workflow_states import placeholder_errors
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.workflow_message_keys import workflow_message_keys


class StepFunctionsSqsHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="SendMessage tasks send the state input unless a constant message is set. Configure consumers, redrive, visibility timeouts, and KMS key policy access separately. FIFO queues require a message group; generated deduplication IDs allow separate executions to send identical payloads.",
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
            and item.target_service == ServiceType.SQS
            and item.connection_type == "sends_message"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(workflow, project)
        if not instance.config.role_arn:
            self._reject(
                connection,
                "role_arn",
                "Workflow SQS tasks require an execution role ARN",
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsSqsConfig.model_validate(item.connection_config)
            target = self._find_instance(item.target_name, project)
            self._validate_queue(item, config, target)
            binding = (
                item.target_name,
                config.message,
                config.message_group_id,
                config.message_deduplication_id,
            )
            if config.state_name in bindings and bindings[config.state_name] != binding:
                self._reject(
                    item,
                    "state_name",
                    "Conflicting SQS queues cannot replace the same workflow state",
                )
            bindings[config.state_name] = binding
        related = (
            (ServiceType.SECRETS_MANAGER, "reads_secret", StepFunctionsSecretConfig),
            (ServiceType.LAMBDA, "invokes", StepFunctionsLambdaConfig),
            (ServiceType.ECS, "runs_task", StepFunctionsEcsConfig),
            (ServiceType.BATCH, "submits_job", StepFunctionsBatchConfig),
            (ServiceType.SNS, "publishes", StepFunctionsSnsConfig),
        )
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
            self._reject(
                connection,
                "state_name",
                f"Workflow state {sorted(overlap)[0]!r} belongs to multiple task connections",
            )
        errors = placeholder_errors(instance.config.definition, set(bindings))
        if errors:
            raise InvalidConnectionConfigError(
                workflow,
                connection.target_name,
                connection.connection_type,
                [{"loc": ("definition",), "msg": error} for error in errors],
            )
        instance.config._sends_sqs_messages = True
        queues = sorted({binding[0] for binding in bindings.values()})
        result = ConnectionContribution()
        for index, name in enumerate(queues):
            result.inputs.extend(
                [
                    ModuleInput(
                        module=workflow,
                        name=f"workflow_sqs_queue_{index}_url",
                        value=f"module.{name}.queue_url",
                    ),
                    ModuleInput(
                        module=workflow,
                        name=f"workflow_sqs_queue_{index}_arn",
                        value=f"module.{name}.queue_arn",
                    ),
                ]
            )
        task_bindings = {}
        for state, (queue, message, group, deduplication) in sorted(bindings.items()):
            target = self._find_instance(queue, project)
            parameters = {
                "QueueUrl": Expr(f"var.workflow_sqs_queue_{queues.index(queue)}_url")
            }
            if message is None:
                parameters["MessageBody.$"] = "States.JsonToString($)"
            else:
                parameters["MessageBody"] = message
            if target.config.fifo_queue:
                parameters["MessageGroupId"] = group
                if deduplication:
                    parameters["MessageDeduplicationId"] = deduplication
                elif not target.config.content_based_deduplication:
                    parameters["MessageDeduplicationId.$"] = "States.UUID()"
            task_bindings[state] = parameters
        result.resources.append(
            self._resource(
                workflow,
                "sqs_tasks.tf",
                sqs_workflow_locals(
                    task_bindings,
                    present[ServiceType.SNS],
                    present[ServiceType.BATCH],
                    present[ServiceType.ECS],
                    present[ServiceType.LAMBDA],
                    present[ServiceType.SECRETS_MANAGER],
                ),
            )
        )
        policy, key_contribution = self._policy(workflow, queues, project)
        result.merge(key_contribution)
        result.resources.append(self._resource(workflow, "sqs_tasks_policy.tf", policy))
        return result

    def _validate_queue(
        self,
        connection: ConnectionIR,
        config: StepFunctionsSqsConfig,
        target: ResourceInstanceIR,
    ) -> None:
        if config.message is not None and (
            not config.message or len(config.message.encode("utf-8")) > 262144
        ):
            self._reject(
                connection, "message", "SQS messages must contain 1–262144 UTF-8 bytes"
            )
        fifo = bool(target.config.fifo_queue)
        if fifo and not (target.config.queue_name or "").endswith(".fifo"):
            self._reject(connection, "queue_name", "FIFO queue names must end in .fifo")
        if fifo and not config.message_group_id:
            self._reject(
                connection, "message_group_id", "FIFO queues require a message group ID"
            )
        if not fifo and (config.message_group_id or config.message_deduplication_id):
            self._reject(
                connection,
                "message_group_id",
                "FIFO message settings require a FIFO queue",
            )

    def _policy(
        self, workflow: str, queues: list[str], project: ProjectIR
    ) -> tuple[str, ConnectionContribution]:
        result, key_resources, data_sources = workflow_message_keys(
            workflow, queues, ServiceType.SQS, project
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": ["sqs:SendMessage"],
                "Resource": [
                    Expr(f"var.workflow_sqs_queue_{index}_arn")
                    for index in range(len(queues))
                ],
            }
        ]
        if key_resources:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
                    "Resource": key_resources,
                }
            )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            "sqs_tasks",
            {
                "name": f"{workflow}-sqs-tasks",
                "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                "policy": self._renderer.render_json_policy(
                    {"Version": "2012-10-17", "Statement": statements}
                ),
            },
        )
        return data_sources + policy, result

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
