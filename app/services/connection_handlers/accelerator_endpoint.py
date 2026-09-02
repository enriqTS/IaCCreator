"""Global Accelerator endpoint wiring owned by accelerator modules."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class AcceleratorLoadBalancerHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        target = safe_identifier(connection.target_name)
        config = connection.connection_config
        listener = self._renderer.render_resource(
            "aws_globalaccelerator_listener",
            f"{target}_listener",
            {
                "accelerator_arn": Expr(
                    f"aws_globalaccelerator_accelerator.{connection.source_name}.id"
                ),
                "protocol": config.get("protocol", "TCP"),
                "client_affinity": "NONE",
                "port_range": [
                    {
                        "from_port": config.get("listener_port", 80),
                        "to_port": config.get("listener_port", 80),
                    }
                ],
            },
        )
        group = self._renderer.render_resource(
            "aws_globalaccelerator_endpoint_group",
            f"{target}_group",
            {
                "listener_arn": Expr(
                    f"aws_globalaccelerator_listener.{target}_listener.id"
                ),
                "health_check_path": config.get("health_check_path", "/"),
                "port_override": [
                    {
                        "listener_port": config.get("listener_port", 80),
                        "endpoint_port": config.get("endpoint_port", 80),
                    }
                ],
                "endpoint_configuration": [
                    {
                        "endpoint_id": Expr(f"var.{target}_load_balancer_arn"),
                        "client_ip_preservation_enabled": True,
                    }
                ],
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.source_name,
                    connection.target_name,
                    "load_balancer_arn",
                    f"module.{connection.target_name}.load_balancer_arn",
                    "Accelerator endpoint load balancer ARN",
                )
            ],
            resources=[
                self._resource(
                    connection.source_name, f"listener_{target}.tf", listener
                ),
                self._resource(
                    connection.source_name, f"endpoint_group_{target}.tf", group
                ),
            ],
        )
