"""Auto Scaling consumes a managed launch template and its concrete latest version."""

from app.exceptions import InvalidConnectionConfigError
from app.models.input_models import ServiceType
from app.models.ir_models import (
    ConnectionContribution,
    ConnectionIR,
    ModuleInput,
    ProjectIR,
)
from app.services.connection_handlers.base import BaseConnectionHandler


class LaunchTemplateAutoScalingHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        sources = {
            item.source_name
            for item in project.connections
            if item.source_service == ServiceType.EC2_LAUNCH_TEMPLATE
            and item.target_name == connection.target_name
            and item.connection_type == "launches"
        }
        if len(sources) > 1:
            raise InvalidConnectionConfigError(
                connection.source_name,
                connection.target_name,
                connection.connection_type,
                [
                    {
                        "loc": ("launch_template_id",),
                        "msg": "An Auto Scaling group can use only one managed launch template",
                    }
                ],
            )
        return ConnectionContribution(
            inputs=[
                ModuleInput(
                    module=connection.target_name,
                    name="launch_template_id",
                    value=f"module.{connection.source_name}.launch_template_id",
                    description="Managed EC2 launch template ID",
                ),
                ModuleInput(
                    module=connection.target_name,
                    name="launch_template_version",
                    value=f"tostring(module.{connection.source_name}.latest_version)",
                    description="Concrete latest version of the managed launch template",
                ),
            ]
        )
