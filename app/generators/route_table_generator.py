"""Terraform generator for route tables."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.route_table_config import RouteTableConfig
from app.models.ir_models import ResourceInstanceIR


class RouteTableGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, RouteTableConfig)
        return self._r.render_resource(
            "aws_route_table",
            instance.name,
            {
                "vpc_id": Expr("var.vpc_id"),
                "route": [
                    {
                        "cidr_block": Expr("var.destination_cidr_block"),
                        "gateway_id": Expr("var.gateway_id"),
                    }
                ],
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, RouteTableConfig)
        return "\n".join(
            [
                self._r.render_variable("vpc_id", "string", "VPC ID"),
                self._r.render_variable(
                    "destination_cidr_block", "string", "Route destination"
                ),
                self._r.render_variable("gateway_id", "string", "Gateway ID"),
            ]
        )

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return self._r.render_output(
            "route_table_id", f"aws_route_table.{instance.name}.id", "Route table ID"
        )
