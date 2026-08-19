"""Lambda → CloudWatch connection handler — the Lambda owns its own log group."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier
from app.services.iam_registry import get_actions


class LambdaCloudWatchHandler(BaseConnectionHandler):
    """Handles Lambda → CloudWatch connections (log group inside the Lambda module)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = connection.source_name
        log_group_name = f"/aws/lambda/{source}"

        content = self._renderer.render_resource(
            "aws_cloudwatch_log_group",
            f"{safe_identifier(source)}_log_group",
            {"name": log_group_name},
        )

        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.CLOUDWATCH, "full"),
            resources=[f"arn:aws:logs:*:*:log-group:{log_group_name}:*"],
        )

        return ConnectionContribution(
            resources=[self._resource(source, "log_group.tf", content)],
            iam=[self._grant(source, statement)],
        )
