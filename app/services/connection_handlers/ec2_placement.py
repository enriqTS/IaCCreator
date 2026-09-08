"""Network placement connections for EC2 instances."""

from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler
from app.services.connection_handlers.network_placement import (
    SecurityGroupListAssociationHandler,
)


class SubnetEC2PlacementHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="subnet_id",
                    value=f"module.{connection.source_name}.subnet_id",
                    description="Subnet for the EC2 instance",
                )
            ]
        )


class SecurityGroupEC2AssociationHandler(SecurityGroupListAssociationHandler):
    pass
