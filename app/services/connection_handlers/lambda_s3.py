"""Lambda → S3 connection handler.

Attaches S3 IAM statements to the Lambda instance based on access_pattern.
Does not generate any HCL files.
"""

import logging

from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionIR, GeneratedFile, IAMStatement, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.iam_registry import get_actions, get_resources

logger = logging.getLogger(__name__)


class LambdaS3Handler(BaseConnectionHandler):
    """Handles Lambda → S3 connections (IAM only, no files)."""

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[GeneratedFile]:
        """Add S3 access IAM statements based on access_pattern config."""
        target = connection.target_name
        access_pattern = connection.connection_config.get("access_pattern", "full")

        actions = get_actions(ServiceType.S3, access_pattern)

        statement = IAMStatement(
            effect="Allow",
            actions=actions,
            resources=get_resources(target, ServiceType.S3),
        )
        self._attach_iam_statement(connection.source_name, statement, project)
        return []
