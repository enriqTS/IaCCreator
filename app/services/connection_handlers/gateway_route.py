"""Gateway routes owned by route-table modules."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class GatewayRouteHandler(BaseConnectionHandler):
    def __init__(self, output_name: str, argument_name: str) -> None:
        super().__init__()
        self._output_name = output_name
        self._argument_name = argument_name

    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        source = safe_identifier(connection.source_name)
        variable = f"{source}_gateway_id"
        destination = connection.connection_config.get(
            "destination_cidr_block", "0.0.0.0/0"
        )
        content = self._renderer.render_resource(
            "aws_route",
            f"{source}_route",
            {
                "route_table_id": Expr(f"aws_route_table.{connection.target_name}.id"),
                "destination_cidr_block": destination,
                self._argument_name: Expr(f"var.{variable}"),
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.target_name,
                    connection.source_name,
                    "gateway_id",
                    f"module.{connection.source_name}.{self._output_name}",
                    "Gateway used by this route",
                )
            ],
            resources=[
                self._resource(
                    connection.target_name,
                    f"route_{source}.tf",
                    content,
                )
            ],
        )
