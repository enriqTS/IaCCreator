"""ConnectionProcessor — thin facade that dispatches to registered connection handlers."""

import logging

from app.models.ir_models import GeneratedFile, ProjectIR
from app.services.connection_handlers.registry import CONNECTION_HANDLER_REGISTRY

logger = logging.getLogger(__name__)


class ConnectionProcessor:
    """Iterates project connections and delegates to the handler registry.

    Each connection type is handled by a dedicated handler class registered
    in CONNECTION_HANDLER_REGISTRY. See app/services/connection_handlers/ for
    individual handler implementations.
    """

    def process_all(self, project: ProjectIR) -> list[GeneratedFile]:
        """Process every connection in the project and return all generated files."""
        files: list[GeneratedFile] = []
        for conn in project.connections:
            handler = CONNECTION_HANDLER_REGISTRY.get(
                (conn.source_service, conn.target_service)
            )
            if handler is None:
                logger.warning(
                    "No handler registered for connection type %s -> %s, skipping",
                    conn.source_service.value,
                    conn.target_service.value,
                )
                continue
            files.extend(handler.handle(conn, project))
        return files
