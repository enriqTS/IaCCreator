"""ConnectionPreviewer — describes each connection's contribution without generating files."""

import logging
import re

from app.models.connection_previews import (
    ConnectionPreview,
    PreviewGrant,
    PreviewResource,
)
from app.models.ir_models import ConnectionContribution, ProjectIR
from app.services.connection_handlers.registry import resolve_spec

logger = logging.getLogger(__name__)

# The HCL renderer is the only thing that writes these headers, so the shape is fixed
_RESOURCE_HEADER = re.compile(r'^resource\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)


class ConnectionPreviewer:
    """Turns each connection's contribution into something the editor can display."""

    def preview_all(self, project: ProjectIR) -> list[ConnectionPreview]:
        """Preview every connection in the project, in the order they were submitted."""
        previews: list[ConnectionPreview] = []
        for conn in project.connections:
            spec = resolve_spec(
                conn.source_service,
                conn.target_service,
                conn.connection_type,
                conn.connection_config,
            )
            if spec is None:
                logger.warning(
                    "No handler registered for connection %s -> %s, skipping preview",
                    conn.source_service.value,
                    conn.target_service.value,
                )
                continue

            contribution = spec.handler.handle(conn, project)
            previews.append(
                ConnectionPreview(
                    source=conn.source_name,
                    target=conn.target_name,
                    source_id=conn.source_id,
                    target_id=conn.target_id,
                    connection_type=spec.connection_type,
                    label=spec.label,
                    resources=self._resources(contribution),
                    iam=self._grants(contribution),
                    issues=spec.handler.validate(conn, project),
                )
            )
        return previews

    @staticmethod
    def _resources(contribution: ConnectionContribution) -> list[PreviewResource]:
        """Name the Terraform resources inside each rendered file the connection emits."""
        return [
            PreviewResource(
                module=emitted.module, resource_type=rtype, resource_name=rname
            )
            for emitted in contribution.resources
            for rtype, rname in _RESOURCE_HEADER.findall(emitted.content)
        ]

    @staticmethod
    def _grants(contribution: ConnectionContribution) -> list[PreviewGrant]:
        return [
            PreviewGrant(
                role_owner=grant.role_owner,
                effect=grant.statement.effect,
                actions=list(grant.statement.actions),
                resources=list(grant.statement.resources),
            )
            for grant in contribution.iam
        ]
