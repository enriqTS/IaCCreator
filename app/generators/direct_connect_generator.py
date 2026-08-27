from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.direct_connect_config import DirectConnectConfig
from app.models.ir_models import ResourceInstanceIR


class DirectConnectGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, DirectConnectConfig)
        return self._r.render_resource(
            "aws_dx_gateway",
            instance.name,
            {
                "name": Expr("var.gateway_name"),
                "amazon_side_asn": Expr("var.amazon_side_asn"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, DirectConnectConfig)
        fields = [
            ("gateway_name", "string", "Direct Connect gateway name"),
            ("amazon_side_asn", "number", "Amazon-side ASN"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_dx_gateway.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "gateway_id", f"{ref}.id", "Direct Connect gateway ID"
                ),
            ]
        )
