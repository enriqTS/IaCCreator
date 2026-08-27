"""VPC membership connections for resources with a vpc_id input."""

from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class VpcMembershipHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = connection.source_name
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="vpc_id",
                    value=f"module.{source}.vpc_id",
                    description=f"VPC ID from {connection.source_name}",
                )
            ]
        )
