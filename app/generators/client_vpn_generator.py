from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.client_vpn_config import ClientVpnConfig
from app.models.ir_models import ResourceInstanceIR


class ClientVpnGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ClientVpnConfig)
        return self._r.render_resource(
            "aws_ec2_client_vpn_endpoint",
            instance.name,
            {
                "description": Expr("var.description"),
                "client_cidr_block": Expr("var.client_cidr_block"),
                "server_certificate_arn": Expr("var.server_certificate_arn"),
                "authentication_options": {
                    "type": "certificate-authentication",
                    "root_certificate_chain_arn": Expr(
                        "var.root_certificate_chain_arn"
                    ),
                },
                "connection_log_options": {"enabled": Expr("false")},
                "split_tunnel": Expr("var.split_tunnel"),
                "transport_protocol": Expr("var.transport_protocol"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ClientVpnConfig)
        fields = [
            ("description", "string", "Endpoint description"),
            ("client_cidr_block", "string", "Client CIDR block"),
            ("server_certificate_arn", "string", "Server certificate ARN"),
            ("root_certificate_chain_arn", "string", "Client root certificate ARN"),
            ("split_tunnel", "bool", "Split tunnel"),
            ("transport_protocol", "string", "Transport protocol"),
            ("tags", "map(string)", "Endpoint tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_ec2_client_vpn_endpoint.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "client_vpn_endpoint_id", f"{ref}.id", "Client VPN endpoint ID"
                ),
                self._r.render_output(
                    "client_vpn_endpoint_arn", f"{ref}.arn", "Client VPN endpoint ARN"
                ),
                self._r.render_output(
                    "dns_name", f"{ref}.dns_name", "Client VPN DNS name"
                ),
            ]
        )
