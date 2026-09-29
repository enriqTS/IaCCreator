"""Workflow-owned EventBridge PutEvents tasks with bus-scoped permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.generators.step_functions_eventbridge import eventbridge_workflow_locals
from app.models.connection_configs.step_functions_dynamodb import (
    StepFunctionsDynamoDbConfig,
)
from app.models.connection_configs.step_functions_eventbridge import (
    StepFunctionsEventBridgeConfig,
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


class StepFunctionsEventBridgeHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return [
            ConnectionIssue(
                severity="warning",
                message="The target rule must match the configured source and detail type, and have a target to deliver the event. Retrying PutEvents can publish duplicate events; configure consumers and error handling accordingly.",
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
            and item.target_service == ServiceType.EVENTBRIDGE
            and item.connection_type == "puts_event"
        ]
        if connection is not peers[0]:
            return ConnectionContribution()
        instance = self._find_instance(workflow, project)
        if not instance.config.role_arn:
            self._reject(
                connection,
                "role_arn",
                "Workflow EventBridge tasks require an execution role ARN",
            )
        bindings = {}
        for item in peers:
            config = StepFunctionsEventBridgeConfig.model_validate(
                item.connection_config
            )
            binding = (item.target_name, config)
            if config.state_name in bindings and bindings[config.state_name] != binding:
                self._reject(
                    item,
                    "state_name",
                    "Conflicting EventBridge events cannot replace the same workflow state",
                )
            bindings[config.state_name] = binding
        related = (
            (ServiceType.SECRETS_MANAGER, "reads_secret", StepFunctionsSecretConfig),
            (ServiceType.LAMBDA, "invokes", StepFunctionsLambdaConfig),
            (ServiceType.ECS, "runs_task", StepFunctionsEcsConfig),
            (ServiceType.BATCH, "submits_job", StepFunctionsBatchConfig),
            (ServiceType.SNS, "publishes", StepFunctionsSnsConfig),
            (ServiceType.SQS, "sends_message", StepFunctionsSqsConfig),
            (ServiceType.DYNAMODB, "accesses_item", StepFunctionsDynamoDbConfig),
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
        instance.config._puts_eventbridge_events = True
        buses = sorted({target for target, _ in bindings.values()})
        result = ConnectionContribution()
        for index, name in enumerate(buses):
            result.inputs.append(
                ModuleInput(
                    module=workflow,
                    name=f"workflow_eventbridge_bus_{index}_arn",
                    value=f"module.{name}.event_bus_arn",
                )
            )
        task_bindings = {}
        for state, (bus, config) in sorted(bindings.items()):
            entry = {
                "EventBusName": Expr(
                    f"var.workflow_eventbridge_bus_{buses.index(bus)}_arn"
                ),
                "Source": config.source,
                "DetailType": config.detail_type,
            }
            if config.detail_json is None:
                entry["Detail.$"] = "States.JsonToString($)"
            else:
                entry["Detail"] = config.detail_json
            task_bindings[state] = {"Entries": [entry]}
        result.resources.append(
            self._resource(
                workflow,
                "eventbridge_tasks.tf",
                eventbridge_workflow_locals(
                    task_bindings,
                    present[ServiceType.DYNAMODB],
                    present[ServiceType.SQS],
                    present[ServiceType.SNS],
                    present[ServiceType.BATCH],
                    present[ServiceType.ECS],
                    present[ServiceType.LAMBDA],
                    present[ServiceType.SECRETS_MANAGER],
                ),
            )
        )
        policy = self._renderer.render_resource(
            "aws_iam_role_policy",
            "eventbridge_tasks",
            {
                "name": f"{workflow}-eventbridge-tasks",
                "role": Expr('element(reverse(split("/", var.role_arn)), 0)'),
                "policy": self._renderer.render_json_policy(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["events:PutEvents"],
                                "Resource": [
                                    Expr(f"var.workflow_eventbridge_bus_{index}_arn")
                                    for index in range(len(buses))
                                ],
                            }
                        ],
                    }
                ),
            },
        )
        result.resources.append(
            self._resource(workflow, "eventbridge_tasks_policy.tf", policy)
        )
        return result

    @staticmethod
    def _reject(connection: ConnectionIR, field: str, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": (field,), "msg": message}],
        )
