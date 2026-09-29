"""Workflow-owned DynamoDB item tasks with operation-scoped table grants."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_dynamodb import dynamodb_workflow_locals
from app.models.connection_configs.step_functions_dynamodb import (
    StepFunctionsDynamoDbConfig,
)
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
)
from app.models.workflow_states import placeholder_errors
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.kms_references import managed_key
from app.services.connection_handlers.step_functions_dynamodb_parameters import (
    OPERATIONS,
    dynamodb_task_parameters,
)
from app.services.connection_handlers.workflow_key_references import (
    workflow_key_references,
)


class StepFunctionsDynamoDbHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="DynamoDB task input paths must resolve to low-level AttributeValue maps containing the table's key attributes. PutItem replaces an existing item unless you supply a condition expression; configure retries and error handling separately.",
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
            and item.target_service == ServiceType.DYNAMODB
            and item.connection_type == "accesses_item"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(workflow, project)
        if not instance.config.role_arn:
            self._reject(
                connection,
                "role_arn",
                "Workflow DynamoDB tasks require an execution role ARN",
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsDynamoDbConfig.model_validate(item.connection_config)
            binding = (item.target_name, config)
            if config.state_name in bindings and bindings[config.state_name] != binding:
                self._reject(
                    item,
                    "state_name",
                    "Conflicting DynamoDB operations cannot replace the same workflow state",
                )
            bindings[config.state_name] = binding
        related = (
            (ServiceType.SECRETS_MANAGER, "reads_secret", StepFunctionsSecretConfig),
            (ServiceType.LAMBDA, "invokes", StepFunctionsLambdaConfig),
            (ServiceType.ECS, "runs_task", StepFunctionsEcsConfig),
            (ServiceType.BATCH, "submits_job", StepFunctionsBatchConfig),
            (ServiceType.SNS, "publishes", StepFunctionsSnsConfig),
            (ServiceType.SQS, "sends_message", StepFunctionsSqsConfig),
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
        instance.config._uses_dynamodb_items = True
        tables = sorted({target for target, _ in bindings.values()})
        for name in tables:
            target = self._find_instance(name, project)
            if (
                target.config.server_side_encryption_kms_key_arn
                and not target.config.server_side_encryption_enabled
                and not managed_key(name, project)
            ):
                self._reject(
                    connection,
                    "server_side_encryption_enabled",
                    "An external DynamoDB KMS key requires server-side encryption to be enabled",
                )
        result = ConnectionContribution()
        for index, name in enumerate(tables):
            result.inputs.extend(
                [
                    ModuleInput(
                        module=workflow,
                        name=f"workflow_dynamodb_table_{index}_name",
                        value=f"module.{name}.table_name",
                    ),
                    ModuleInput(
                        module=workflow,
                        name=f"workflow_dynamodb_table_{index}_arn",
                        value=f"module.{name}.table_arn",
                    ),
                ]
            )
        task_bindings = {}
        actions_to_tables = {}
        for state, (table, config) in sorted(bindings.items()):
            action = OPERATIONS[config.operation]
            index = tables.index(table)
            task_bindings[state] = {
                "operation": action,
                "parameters": dynamodb_task_parameters(
                    config, f"workflow_dynamodb_table_{index}_name"
                ),
            }
            actions_to_tables.setdefault(action, set()).add(index)
        result.resources.append(
            self._resource(
                workflow,
                "dynamodb_tasks.tf",
                dynamodb_workflow_locals(
                    task_bindings,
                    present[ServiceType.SQS],
                    present[ServiceType.SNS],
                    present[ServiceType.BATCH],
                    present[ServiceType.ECS],
                    present[ServiceType.LAMBDA],
                    present[ServiceType.SECRETS_MANAGER],
                ),
            )
        )
        policy, key_contribution = self._policy(
            workflow, tables, actions_to_tables, project
        )
        result.merge(key_contribution)
        result.resources.append(
            self._resource(
                workflow,
                "dynamodb_tasks_policy.tf",
                policy,
            )
        )
        return result

    def _policy(
        self,
        workflow: str,
        tables: list[str],
        actions_to_tables: dict[str, set[int]],
        project: ProjectIR,
    ) -> tuple[str, ConnectionContribution]:
        result, key_resources, data_sources = workflow_key_references(
            workflow, tables, ServiceType.DYNAMODB, project
        )
        statements = [
            {
                "Effect": "Allow",
                "Action": [f"dynamodb:{action[0].upper()}{action[1:]}"],
                "Resource": [
                    Expr(f"var.workflow_dynamodb_table_{index}_arn")
                    for index in sorted(actions_to_tables[action])
                ],
            }
            for action in sorted(actions_to_tables)
        ]
        if key_resources:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt"],
                    "Resource": key_resources,
                }
            )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            "dynamodb_tasks",
            {
                "name": f"{workflow}-dynamodb-tasks",
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
