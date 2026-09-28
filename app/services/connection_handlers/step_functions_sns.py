"""Workflow-owned SNS Publish tasks and topic-scoped permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_sns import sns_workflow_locals
from app.models.connection_configs.workflows import (
    StepFunctionsBatchConfig,
    StepFunctionsEcsConfig,
    StepFunctionsLambdaConfig,
    StepFunctionsSecretConfig,
    StepFunctionsSnsConfig,
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
from app.services.connection_handlers.kms_references import managed_key


class StepFunctionsSnsHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="Publish tasks send the state input unless a constant message is set. Configure subscribers, delivery monitoring, and KMS key policy access separately. FIFO topics require a message group; generated deduplication IDs allow separate executions to publish identical payloads.",
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
            and item.target_service == ServiceType.SNS
            and item.connection_type == "publishes"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(workflow, project)
        if not instance.config.role_arn:
            self._reject(
                connection,
                "role_arn",
                "Workflow SNS tasks require an execution role ARN",
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsSnsConfig.model_validate(item.connection_config)
            target = self._find_instance(item.target_name, project)
            self._validate_topic(item, config, target)
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
                    "Conflicting SNS topics cannot replace the same workflow state",
                )
            bindings[config.state_name] = binding
        related = (
            (ServiceType.SECRETS_MANAGER, "reads_secret", StepFunctionsSecretConfig),
            (ServiceType.LAMBDA, "invokes", StepFunctionsLambdaConfig),
            (ServiceType.ECS, "runs_task", StepFunctionsEcsConfig),
            (ServiceType.BATCH, "submits_job", StepFunctionsBatchConfig),
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
        instance.config._publishes_sns_messages = True
        topics = sorted({binding[0] for binding in bindings.values()})
        result = ConnectionContribution()
        for index, name in enumerate(topics):
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=f"workflow_sns_topic_{index}_arn",
                    value=f"module.{name}.topic_arn",
                )
            )
        task_bindings = {}
        for state, (topic, message, group, deduplication) in sorted(bindings.items()):
            target = self._find_instance(topic, project)
            parameters = {
                "TopicArn": Expr(f"var.workflow_sns_topic_{topics.index(topic)}_arn")
            }
            if message is None:
                parameters["Message.$"] = "States.JsonToString($)"
            else:
                parameters["Message"] = message
            if target.config.fifo_topic:
                parameters["MessageGroupId"] = group
                if deduplication:
                    parameters["MessageDeduplicationId"] = deduplication
                elif not target.config.content_based_deduplication:
                    parameters["MessageDeduplicationId.$"] = "States.UUID()"
            task_bindings[state] = parameters
        result.resources.append(
            self._resource(
                workflow,
                "sns_tasks.tf",
                sns_workflow_locals(
                    task_bindings,
                    present[ServiceType.BATCH],
                    present[ServiceType.ECS],
                    present[ServiceType.LAMBDA],
                    present[ServiceType.SECRETS_MANAGER],
                ),
            )
        )
        policy, key_contribution = self._policy(workflow, topics, project)
        result.merge(key_contribution)
        result.resources.append(self._resource(workflow, "sns_tasks_policy.tf", policy))
        return result

    def _validate_topic(
        self,
        connection: ConnectionIR,
        config: StepFunctionsSnsConfig,
        target: ResourceInstanceIR,
    ) -> None:
        if config.message is not None and (
            not config.message or len(config.message.encode("utf-8")) > 262144
        ):
            self._reject(
                connection, "message", "SNS messages must contain 1–262144 UTF-8 bytes"
            )
        fifo = bool(target.config.fifo_topic)
        if fifo and not (target.config.topic_name or "").endswith(".fifo"):
            self._reject(connection, "topic_name", "FIFO topic names must end in .fifo")
        if fifo and not config.message_group_id:
            self._reject(
                connection, "message_group_id", "FIFO topics require a message group ID"
            )
        if not fifo and (config.message_group_id or config.message_deduplication_id):
            self._reject(
                connection,
                "message_group_id",
                "FIFO message settings require a FIFO topic",
            )

    def _policy(
        self, workflow: str, topics: list[str], project: ProjectIR
    ) -> tuple[str, ConnectionContribution]:
        result = ConnectionContribution()
        statements = [
            {
                "Effect": "Allow",
                "Action": ["sns:Publish"],
                "Resource": [
                    Expr(f"var.workflow_sns_topic_{index}_arn")
                    for index in range(len(topics))
                ],
            }
        ]
        data_sources = []
        key_resources = []
        for index, topic in enumerate(topics):
            target = self._find_instance(topic, project)
            key = managed_key(topic, project)
            external = target.config.kms_master_key_id
            if not key and not external:
                continue
            variable = f"workflow_sns_key_{index}_arn"
            if key:
                result.inputs.append(
                    ModuleInput(
                        module=workflow,
                        name=variable,
                        value=f"module.{key}.key_arn",
                    )
                )
                key_resources.append(Expr(f"var.{variable}"))
            else:
                result.outputs.append(
                    self._output(topic, "kms_access_key_id", "var.kms_master_key_id")
                )
                result.inputs.append(
                    ModuleInput(
                        module=workflow,
                        name=variable,
                        value=f"module.{topic}.kms_access_key_id",
                    )
                )
                data_sources.append(
                    f'data "aws_kms_key" "{variable}" {{\n  key_id = var.{variable}\n}}\n'
                )
                key_resources.append(Expr(f"data.aws_kms_key.{variable}.arn"))
        if key_resources:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt", "kms:GenerateDataKey*"],
                    "Resource": key_resources,
                }
            )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            "sns_tasks",
            {
                "name": f"{workflow}-sns-tasks",
                "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                "policy": self._renderer.render_json_policy(
                    {"Version": "2012-10-17", "Statement": statements}
                ),
            },
        )
        return "".join(data_sources) + policy, result

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
