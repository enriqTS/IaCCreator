"""Reusable network placement connection handlers."""

from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class ListPlacementHandler(BaseConnectionHandler):
    def __init__(
        self,
        source_service: ServiceType,
        connection_type: str,
        input_name: str,
        output_name: str,
        description: str,
    ) -> None:
        super().__init__()
        self._source_service = source_service
        self._connection_type = connection_type
        self._input_name = input_name
        self._output_name = output_name
        self._description = description

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = self._find_instance(connection.target_name, project)
        if target is not None and not getattr(target.config, self._input_name, None):
            setattr(target.config, self._input_name, ["managed-by-connection"])
        sources = sorted(
            {
                item.source_name
                for item in project.connections
                if item.target_name == connection.target_name
                and item.source_service == self._source_service
                and item.connection_type == self._connection_type
            }
        )
        references = ", ".join(f"module.{name}.{self._output_name}" for name in sources)
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name=self._input_name,
                    value=f"[{references}]",
                    type="list(string)",
                    description=self._description,
                )
            ]
        )


class SubnetListPlacementHandler(ListPlacementHandler):
    def __init__(self, input_name: str = "subnet_ids") -> None:
        super().__init__(
            ServiceType.SUBNET,
            "places",
            input_name,
            "subnet_id",
            "Subnets selected for this workload",
        )


class SecurityGroupListAssociationHandler(ListPlacementHandler):
    def __init__(self, input_name: str = "security_group_ids") -> None:
        super().__init__(
            ServiceType.SECURITY_GROUP,
            "associates",
            input_name,
            "security_group_id",
            "Security groups associated with this workload",
        )
