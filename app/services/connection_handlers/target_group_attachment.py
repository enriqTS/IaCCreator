"""Target attachments owned by target-group modules."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models.target_group_config import TargetGroupConfig
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class TargetGroupEC2AttachmentHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        variable = f"{target}_instance_id"
        attrs: dict[str, object] = {
            "target_group_arn": Expr(
                f"aws_lb_target_group.{connection.source_name}.arn"
            ),
            "target_id": Expr(f"var.{variable}"),
        }
        port = connection.connection_config.get("port")
        if port is not None:
            attrs["port"] = port
        content = self._renderer.render_resource(
            "aws_lb_target_group_attachment",
            f"{target}_attachment",
            attrs,
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "instance_id",
                    f"module.{connection.target_name}.instance_id",
                    "EC2 instance registered with this target group",
                )
            ],
            resources=[
                self._resource(
                    connection.source_name,
                    f"attachment_{target}.tf",
                    content,
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        group = self._find_instance(connection.source_name, project)
        if group is None or not isinstance(group.config, TargetGroupConfig):
            return []
        if group.config.target_type != "instance":
            return [
                ConnectionIssue(
                    severity="error",
                    message="EC2 attachments require an instance target group",
                )
            ]
        return []
