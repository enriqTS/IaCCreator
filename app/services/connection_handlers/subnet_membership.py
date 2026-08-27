"""Subnet placement connections for resources with a subnet_id input."""

from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class SubnetMembershipHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="subnet_id",
                    value=f"module.{connection.source_name}.subnet_id",
                    description=f"Subnet ID from {connection.source_name}",
                )
            ]
        )
