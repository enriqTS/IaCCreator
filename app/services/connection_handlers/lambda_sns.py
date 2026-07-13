"""Lambda → SNS connection handler.

Attaches SNS publish IAM statements to the Lambda instance.
Always uses "full" access pattern (sns:Publish). Does not generate any HCL files.
"""

import logging

from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, IAMStatement, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources

logger = logging.getLogger(__name__)


class LambdaSNSHandler(BaseConnectionHandler):
    """Handles Lambda → SNS connections (IAM only, no files)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Add SNS publish IAM statements to the Lambda instance."""
        target = connection.target_name

        actions = get_actions(ServiceType.SNS, "full")

        statement = IAMStatement(
            effect="Allow",
            actions=actions,
            resources=get_resources(target, ServiceType.SNS),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []
