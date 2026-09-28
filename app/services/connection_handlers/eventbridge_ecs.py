"""EventBridge runs the connected ECS Fargate task with scoped permissions."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_ecs import EventBridgeEcsConfig
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeEcsHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeEcsConfig

    def __init__(self):
        super().__init__(
            "ecs",
            "ecs:RunTask",
            "cluster_arn",
            "Runs the connected ECS Fargate task on matching events. Configure networking, application idempotency, retries, dead-letter handling, and monitoring separately.",
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        config = target.config
        managed_subnets = any(
            peer.source_service == ServiceType.SUBNET
            and peer.target_name == connection.target_name
            and peer.connection_type == "places"
            for peer in project.connections
        )
        external_subnets = any(
            value != "managed-by-connection" for value in config.subnet_ids
        )
        if config.ecs_launch_type not in (None, "FARGATE") or not (
            external_subnets or managed_subnets
        ):
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("subnet_ids",),
                        "msg": "EventBridge ECS targets require Fargate and at least one task subnet",
                    }
                ],
            )
        if managed_subnets and not config.subnet_ids:
            config.subnet_ids = ["managed-by-connection"]
        config._requires_task_role = True
        return super().handle(connection, project)

    def grant_resource(self, variable: str, config: EventBridgeEcsConfig) -> str:
        return "${var." + variable.removesuffix("_arn") + "_task_arn}"

    def additional_inputs(
        self, rule: str, destination: str, identifier: str, config: EventBridgeEcsConfig
    ) -> list[ModuleInput]:
        return [
            ModuleInput(
                module=rule,
                name=f"{identifier}_{name}",
                value=f"module.{destination}.{output}",
                type=kind,
            )
            for name, output, kind in (
                ("task_arn", "task_definition_arn", "string"),
                ("task_role_arn", "task_role_arn", "string"),
                ("subnet_ids", "subnet_ids", "list(string)"),
                ("security_group_ids", "security_group_ids", "list(string)"),
                ("assign_public_ip", "assign_public_ip", "bool"),
            )
        ]

    def policy_statements(
        self,
        statements: list[dict],
        variable: str,
        identifier: str,
        config: EventBridgeEcsConfig,
    ) -> list[dict]:
        statements[0]["Condition"] = {
            "ArnEquals": {"ecs:cluster": Expr(f"var.{variable}")}
        }
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": [Expr(f"var.{identifier}_task_role_arn")],
                "Condition": {
                    "StringEquals": {"iam:PassedToService": "ecs-tasks.amazonaws.com"}
                },
            }
        )
        return statements

    def target_attributes(self, config: EventBridgeEcsConfig, identifier: str) -> dict:
        return {
            "ecs_target": {
                "task_definition_arn": Expr(f"var.{identifier}_task_arn"),
                "task_count": config.task_count,
                "launch_type": "FARGATE",
                "network_configuration": {
                    "subnets": Expr(f"var.{identifier}_subnet_ids"),
                    "security_groups": Expr(f"var.{identifier}_security_group_ids"),
                    "assign_public_ip": Expr(f"var.{identifier}_assign_public_ip"),
                },
            }
        }
