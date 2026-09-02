"""Listeners owned by load-balancer modules."""

from app.generators.hcl_renderer import Expr
from app.models.connection_previews import ConnectionIssue
from app.models.input_models import ServiceType
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class LoadBalancerTargetGroupHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        variable = f"{target}_target_group_arn"
        config = connection.connection_config
        protocol = config.get("protocol", "HTTP")
        certificates = sorted(
            item.source_name
            for item in project.connections
            if item.source_service == ServiceType.CERTIFICATE_MANAGER
            and item.target_name == connection.source_name
            and item.connection_type == "secures"
        )
        attrs: dict[str, object] = {
            "load_balancer_arn": Expr(f"aws_lb.{connection.source_name}.arn"),
            "port": config.get("port", 80),
            "protocol": protocol,
            "default_action": [
                {
                    "type": "forward",
                    "target_group_arn": Expr(f"var.{variable}"),
                }
            ],
        }
        if protocol in {"HTTPS", "TLS"} and certificates:
            certificate = safe_identifier(certificates[0])
            attrs["certificate_arn"] = Expr(f"var.{certificate}_certificate_arn")
            attrs["ssl_policy"] = "ELBSecurityPolicy-TLS13-1-2-2021-06"
        content = self._renderer.render_resource(
            "aws_lb_listener", f"{target}_listener", attrs
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
        has_certificate = any(
            item.source_service == ServiceType.CERTIFICATE_MANAGER
            and item.target_name == connection.source_name
            and item.connection_type == "secures"
            for item in project.connections
        )
        if protocol in {"HTTPS", "TLS"} and not has_certificate:
            return [
                ConnectionIssue(
                    severity="error",
                    message="HTTPS and TLS listeners require a certificate connection",
                )
            ]
        return []
