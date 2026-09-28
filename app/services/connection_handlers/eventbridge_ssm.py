"""EventBridge sends a managed Command document to one EC2 instance."""

from app.exceptions import InvalidConnectionConfigError
from app.generators.hcl_renderer import Expr
from app.models.connection_configs.eventbridge_ssm import EventBridgeSsmConfig
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.eventbridge_role_target import (
    EventBridgeRoleTargetHandler,
)


class EventBridgeSsmHandler(EventBridgeRoleTargetHandler):
    config_model = EventBridgeSsmConfig

    def __init__(self):
        super().__init__(
            "ssm",
            "ssm:SendCommand",
            "document_arn",
            "Sends the connected Command document to the selected managed EC2 instance. Ensure the instance has SSM Agent, an instance profile, and network access to Systems Manager.",
        )

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        document = self._find_instance(connection.target_name, project)
        if document.config.document_type != "Command":
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("document_type",),
                        "msg": "Run Command requires a Command document",
                    }
                ],
            )
        return super().handle(connection, project)

    def additional_inputs(
        self, rule: str, destination: str, identifier: str, config: EventBridgeSsmConfig
    ) -> list[ModuleInput]:
        return [
            ModuleInput(
                module=rule,
                name=f"{identifier}_document_type",
                value=f"module.{destination}.document_type",
            )
        ]

    def data_sources(self, identifier: str, config: EventBridgeSsmConfig) -> list[str]:
        return [
            f'data "aws_partition" "{identifier}" {{}}\n',
            f'data "aws_region" "{identifier}" {{}}\n',
            f'data "aws_caller_identity" "{identifier}" {{}}\n',
        ]

    def policy_statements(
        self,
        statements: list[dict],
        variable: str,
        identifier: str,
        config: EventBridgeSsmConfig,
    ) -> list[dict]:
        statements[0]["Resource"].append(
            Expr(
                'format("arn:%s:ec2:%s:%s:instance/%s", '
                f"data.aws_partition.{identifier}.partition, "
                f"data.aws_region.{identifier}.name, "
                f"data.aws_caller_identity.{identifier}.account_id, "
                f'"{config.instance_id}")'
            )
        )
        return statements

    def target_attributes(self, config: EventBridgeSsmConfig, identifier: str) -> dict:
        return {
            "run_command_targets": {
                "key": "InstanceIds",
                "values": [config.instance_id],
            },
            "lifecycle": {
                "precondition": [
                    {
                        "condition": Expr(
                            f'var.{identifier}_document_type == "Command"'
                        ),
                        "error_message": "Run Command requires a Command document.",
                    }
                ]
            },
        }
