"""Terraform generator for internet gateways."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.internet_gateway_config import InternetGatewayConfig
from app.models.ir_models import ResourceInstanceIR


class InternetGatewayGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, InternetGatewayConfig)
        return self._r.render_resource(
            "aws_internet_gateway",
            instance.name,
            {"vpc_id": Expr("var.vpc_id")},
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        return self._r.render_variable("vpc_id", "string", "VPC ID")

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        return "\n".join(
            [
                self._r.render_output(
                    "internet_gateway_id",
                    f"aws_internet_gateway.{instance.name}.id",
                    "Internet gateway ID",
                ),
                self._r.render_output(
                    "internet_gateway_arn",
                    f"aws_internet_gateway.{instance.name}.arn",
                    "Internet gateway ARN",
                ),
            ]
        )
