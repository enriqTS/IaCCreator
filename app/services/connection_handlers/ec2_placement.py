"""Network placement connections for EC2 instances."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


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


class SecurityGroupEC2AssociationHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        groups = sorted(
            {
                item.source_name
                for item in project.connections
                if item.target_name == connection.target_name
                and item.source_service == ServiceType.SECURITY_GROUP
                and item.connection_type == "associates"
            }
        )
        references = ", ".join(f"module.{name}.security_group_id" for name in groups)
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="security_group_ids",
                    value=f"[{references}]",
                    type="list(string)",
                    description="Security groups associated with the EC2 instance",
                )
            ]
        )
