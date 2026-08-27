from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.transit_gateway_config import TransitGatewayConfig
from app.models.ir_models import ResourceInstanceIR


class TransitGatewayGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TransitGatewayConfig)
        return self._r.render_resource(
            "aws_ec2_transit_gateway",
            instance.name,
            {
                "description": Expr("var.description"),
                "amazon_side_asn": Expr("var.amazon_side_asn"),
                "dns_support": Expr('var.dns_support ? "enable" : "disable"'),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TransitGatewayConfig)
        fields = [
            ("description", "string", "Transit gateway description"),
            ("amazon_side_asn", "number", "Amazon-side ASN"),
            ("dns_support", "bool", "Enable DNS support"),
            ("tags", "map(string)", "Transit gateway tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_ec2_transit_gateway.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "transit_gateway_id", f"{ref}.id", "Transit gateway ID"
                ),
                self._r.render_output(
                    "transit_gateway_arn", f"{ref}.arn", "Transit gateway ARN"
                ),
            ]
        )
