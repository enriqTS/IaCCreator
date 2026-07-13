"""Lambda → DynamoDB connection handler.

Attaches DynamoDB IAM statements to the Lambda instance based on access_pattern.
Does not generate any HCL files.
"""

import logging

from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, IAMStatement, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources

logger = logging.getLogger(__name__)


class LambdaDynamoDBHandler(BaseConnectionHandler):
    """Handles Lambda → DynamoDB connections (IAM only, no files)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Add DynamoDB read/write IAM statements based on access_pattern config."""
        target = connection.target_name
        access_pattern = connection.connection_config.get("access_pattern", "full")

        actions = get_actions(ServiceType.DYNAMODB, access_pattern)

        statement = IAMStatement(
            effect="Allow",
            actions=actions,
            resources=get_resources(target, ServiceType.DYNAMODB),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []
