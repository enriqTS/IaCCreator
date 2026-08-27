"""Private Route 53 hosted-zone association with a diagram VPC."""

from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class Route53VpcAssociationHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="vpc_id",
                    value=f"module.{connection.source_name}.vpc_id",
                    description=f"VPC ID from {connection.source_name}",
                ),
                ModuleInput(
                    module=connection.target_name,
                    name="private_zone",
                    value="true",
                    description="Private hosted zone enabled by VPC containment",
                ),
            ]
        )
