"""Lambda writes to the connected log group, including its encryption configuration."""

from app.exceptions import InvalidConnectionConfigError
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.connection_handlers.kms_consumer import KmsConsumerGrants
from app.services.connection_handlers.kms_external_policy import (
    external_service_key_issues,
)


class LambdaCloudWatchHandler(BaseConnectionHandler):
    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        return external_service_key_issues(connection, project)

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        targets = {
            item.target_name
            for item in project.connections
            if item.source_name == connection.source_name
            and item.target_service == ServiceType.CLOUDWATCH
        }
        if len(targets) > 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("target",),
                        "msg": "A Lambda function can use only one log group",
                    }
                ],
            )
        function = self._find_instance(connection.source_name, project)
        if function is not None:
            function.config.logging_log_group = "managed-by-connection"
            if function.config.logging_log_format is None:
                function.config.logging_log_format = "Text"
        target = connection.target_name
        variable = f"{safe_identifier(target)}_log_group_arn"
        result = ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    target,
                    "log_group_arn",
                    f"module.{target}.log_group_arn",
                    "Connected log group ARN",
                ),
            ],
            outputs=[
                self._output(
                    target,
                    "log_group_name",
                    "var.log_group_name",
                    "Connected log group name",
                )
            ],
            iam=[
                self._grant(
                    connection.source_name,
                    IAMStatement(
                        actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                        resources=["${var." + variable + "}:*"],
                    ),
                )
            ],
        )
        from app.models.ir_models import ModuleInput

        result.inputs.append(
            ModuleInput(
                module=connection.source_name,
                name="logging_log_group",
                value=f"module.{target}.log_group_name",
                description="Connected CloudWatch log group",
            )
        )
        return KmsConsumerGrants().augment(result, target, project)
