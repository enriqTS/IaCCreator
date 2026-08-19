"""Lambda → SNS connection handler — grants the Lambda access to the target."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources


class LambdaSNSHandler(BaseConnectionHandler):
    """Handles Lambda → SNS connections, which only add IAM to the source Lambda."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = connection.target_name
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(ServiceType.SNS, "full"),
            resources=get_resources(target, ServiceType.SNS),
        )
        return ConnectionContribution(
            iam=[self._grant(connection.source_name, statement)]
        )
