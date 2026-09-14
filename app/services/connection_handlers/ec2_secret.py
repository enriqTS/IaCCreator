"""Connection-owned EC2 credentials for runtime secret retrieval."""

from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.ec2_runtime_role import Ec2RuntimeRole
from app.services.connection_handlers.secret_access import SecretAccessHandler


class Ec2SecretHandler(SecretAccessHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        result = super().handle(connection, project)
        if not result.resources:
            return result
        instance = self._find_instance(connection.source_name, project)
        if instance is not None:
            instance.config._reads_runtime_secrets = True
        result.merge(Ec2RuntimeRole().build(connection.source_name))
        return result
