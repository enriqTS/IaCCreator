"""ECS service load-balancer wiring."""

from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class TargetGroupECSHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        service = self._find_instance(connection.target_name, project)
        connections = sorted(
            (
                item
                for item in project.connections
                if item.source_service == ServiceType.TARGET_GROUP
                and item.target_name == connection.target_name
                and item.connection_type == "serves"
            ),
            key=lambda item: item.source_name,
        )
        if service is not None:
            service.config.ecs_load_balancers = [
                {
                    "variable_name": f"{safe_identifier(item.source_name)}_target_group_arn",
                    "container_name": item.connection_config.get("container_name")
                    or connection.target_name,
                    "container_port": item.connection_config.get("container_port", 80),
                }
                for item in connections
            ]
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.target_name,
                    connection.source_name,
                    "target_group_arn",
                    f"module.{connection.source_name}.target_group_arn",
                    "Target group served by this ECS service",
                )
            ]
        )
