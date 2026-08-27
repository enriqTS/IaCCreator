"""Subnet to route-table association connection."""

from app.generators.hcl_renderer import Expr
from app.models.ir_models import ConnectionContribution, ConnectionIR, ProjectIR
from app.services.connection_handlers.base import BaseConnectionHandler, safe_identifier


class RouteTableAssociationHandler(BaseConnectionHandler):
    def handle(
        self, connection: ConnectionIR, project: ProjectIR
    ) -> ConnectionContribution:
        subnet = safe_identifier(connection.source_name)
        variable = f"{subnet}_subnet_id"
        content = self._renderer.render_resource(
            "aws_route_table_association",
            f"{subnet}_association",
            {
                "subnet_id": Expr(f"var.{variable}"),
                "route_table_id": Expr(f"aws_route_table.{connection.target_name}.id"),
            },
        )
        return ConnectionContribution(
            inputs=[
                self._input(
                    connection.target_name,
                    connection.source_name,
                    "subnet_id",
                    f"module.{connection.source_name}.subnet_id",
                    "Subnet associated with this route table",
                )
            ],
            resources=[
                self._resource(
                    connection.target_name,
                    f"association_{subnet}.tf",
                    content,
                )
            ],
        )
