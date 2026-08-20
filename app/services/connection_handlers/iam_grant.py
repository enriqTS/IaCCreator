"""Connections whose only effect is granting the source access to the target."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    IAMStatement,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources


class IamGrantHandler(BaseConnectionHandler):
    """Grants the source resource's execution role access to the target."""

    def __init__(self, target_service: ServiceType, access_pattern: str | None = None):
        super().__init__()
        self._target_service = target_service
        # A fixed pattern means the connection offers no access choice
        self._access_pattern = access_pattern

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        access_pattern = self._access_pattern or connection.connection_config.get(
            "access_pattern", "full"
        )
        statement = IAMStatement(
            effect="Allow",
            actions=get_actions(self._target_service, access_pattern),
            resources=get_resources(connection.target_name, self._target_service),
        )
        return ConnectionContribution(
            iam=[self._grant(connection.source_name, statement)]
        )
