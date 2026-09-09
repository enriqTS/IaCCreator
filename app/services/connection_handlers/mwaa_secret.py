"""MWAA DAG runtime secret reads using the environment execution role."""

from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.external_role_secret import (
    ExternalRoleSecretAccessHandler,
)


class MwaaSecretHandler(ExternalRoleSecretAccessHandler):
    def __init__(self) -> None:
        super().__init__("execution_role_arn", "MWAA")

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        result = super().handle(connection, project)
        if result.resources:
            instance = self._find_instance(connection.source_name, project)
            instance.config._reads_runtime_secrets = True
        return result
