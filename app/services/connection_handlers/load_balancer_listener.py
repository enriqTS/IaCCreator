"""Listeners owned by load-balancer modules."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class LoadBalancerTargetGroupHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        variable = f"{target}_target_group_arn"
        config = connection.connection_config
        content = self._renderer.render_resource(
            "aws_lb_listener",
            f"{target}_listener",
            {
                "load_balancer_arn": Expr(f"aws_lb.{connection.source_name}.arn"),
                "port": config.get("port", 80),
                "protocol": config.get("protocol", "HTTP"),
                "default_action": [
                    {
                        "type": "forward",
                        "target_group_arn": Expr(f"var.{variable}"),
                    }
                ],
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "target_group_arn",
                    f"module.{connection.target_name}.target_group_arn",
                    "Default target group for this listener",
                )
            ],
            resources=[
                self._resource(
                    connection.source_name,
                    f"listener_{target}.tf",
                    content,
                )
            ],
        )

    def validate(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> list[ConnectionIssue]:
        protocol = connection.connection_config.get("protocol", "HTTP")
        if protocol in {"HTTPS", "TLS"}:
            return [
                ConnectionIssue(
                    severity="error",
                    message="HTTPS and TLS listeners require a certificate connection",
                )
            ]
        return []
