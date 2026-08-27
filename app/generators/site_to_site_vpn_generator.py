from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.site_to_site_vpn_config import SiteToSiteVpnConfig
from app.models.ir_models import ResourceInstanceIR


class SiteToSiteVpnGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SiteToSiteVpnConfig)
        return self._r.render_resource(
            "aws_vpn_connection",
            instance.name,
            {
                "customer_gateway_id": Expr("var.customer_gateway_id"),
                "transit_gateway_id": Expr("var.transit_gateway_id"),
                "type": "ipsec.1",
                "static_routes_only": Expr("var.static_routes_only"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, SiteToSiteVpnConfig)
        fields = [
            ("customer_gateway_id", "string", "Customer gateway ID"),
            ("transit_gateway_id", "string", "Transit gateway ID"),
            ("static_routes_only", "bool", "Static routes only"),
            ("tags", "map(string)", "VPN tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_vpn_connection.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "vpn_connection_id", f"{ref}.id", "VPN connection ID"
                ),
                self._r.render_output(
                    "vpn_connection_arn", f"{ref}.arn", "VPN connection ARN"
                ),
            ]
        )
