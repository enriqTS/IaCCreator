"""ConnectionProcessor — thin facade that dispatches to registered connection handlers."""

import logging

from app.generators.iam_references import cross_module_inputs
from app.models.ir_models import ConnectionContribution, ProjectIR
from app.services.connection_handlers.registry import resolve_spec

logger = logging.getLogger(__name__)


class ConnectionProcessor:
    """Iterates project connections and merges what each handler contributes."""

    def process_all(self, project: ProjectIR) -> ConnectionContribution:
        """Process every connection and return one merged contribution."""
        merged = ConnectionContribution()
        for conn in project.connections:
            spec = resolve_spec(
                conn.source_service,
                conn.target_service,
                conn.connection_type,
                conn.connection_config,
            )
            if spec is None:
                logger.warning(
                    "No handler registered for connection type %s -> %s, skipping",
                    conn.source_service.value,
                    conn.target_service.value,
                )
                continue
            merged.merge(spec.handler.handle(conn, project))

        self._attach_iam(merged, project)
        merged.inputs.sort(key=lambda item: (item.module, item.name))
        merged.outputs.sort(key=lambda item: (item.module, item.name))
        return merged

    @staticmethod
    def _attach_iam(contribution: ConnectionContribution, project: ProjectIR) -> None:
        """Move collected IAM statements onto the instances that own the roles."""
        instances = {
            inst.name: inst for module in project.modules for inst in module.instances
        }
        for grant in contribution.iam:
            instance = instances.get(grant.role_owner)
            if instance is not None and grant.statement not in instance.iam_statements:
                instance.iam_statements.append(grant.statement)
        for instance in instances.values():
            instance.iam_statements.sort(
                key=lambda statement: statement.model_dump_json()
            )
            contribution.merge(cross_module_inputs(instance))
