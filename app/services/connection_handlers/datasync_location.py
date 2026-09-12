"""DataSync tasks reference separately owned transfer locations."""

from app.exceptions import InvalidConnectionConfigError
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class DataSyncLocationHandler(BaseConnectionHandler):
    def __init__(self, field: str) -> None:
        super().__init__()
        self.field = field

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        peers = [
            item
            for item in project.connections
            if item.source_name == connection.source_name
            and item.connection_type in {"reads_from", "writes_to"}
        ]
        targets = {
            item.target_name
            for item in peers
            if item.connection_type == connection.connection_type
        }
        other_targets = {
            item.target_name
            for item in peers
            if item.connection_type != connection.connection_type
        }
        target = self._find_instance(connection.target_name, project)
        if len(targets) != 1 or targets & other_targets:
            self._reject(
                connection,
                "A DataSync task requires one distinct location for each transfer direction",
            )
        if self.field == "destination_location_arn" and target.config.access != "write":
            self._reject(connection, "A destination location requires write access")
        source = self._find_instance(connection.source_name, project)
        setattr(source.config, self.field, "managed-by-connection")
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=source.name,
                    name=self.field,
                    value=f"module.{target.name}.location_arn",
                    description="Managed DataSync transfer location",
                )
            ]
        )

    @staticmethod
    def _reject(connection: ConnectionIR, message: str) -> None:
        raise InvalidConnectionConfigError(
            connection.source_name,
            connection.target_name,
            connection.connection_type,
            [{"loc": ("location",), "msg": message}],
        )
