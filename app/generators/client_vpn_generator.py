from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.client_vpn_config import ClientVpnConfig
from app.models.ir_models import ResourceInstanceIR


class ClientVpnGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, ClientVpnConfig)
        endpoint = self._r.render_resource(
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
                "security_group_ids": Expr("var.security_group_ids"),
                "tags": Expr("var.tags"),
            },
        )
        if not config.subnet_ids:
            return endpoint
        association = self._r.render_resource(
            "aws_ec2_client_vpn_network_association",
            instance.name,
            {
                "for_each": Expr("toset(var.subnet_ids)"),
                "client_vpn_endpoint_id": Expr(
                    f"aws_ec2_client_vpn_endpoint.{instance.name}.id"
                ),
                "subnet_id": Expr("each.value"),
            },
        )
        return f"{endpoint}\n{association}"

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, ClientVpnConfig)
        fields = [
            ("description", "string", "Endpoint description"),
            ("client_cidr_block", "string", "Client CIDR block"),
            ("server_certificate_arn", "string", "Server certificate ARN"),
            ("root_certificate_chain_arn", "string", "Client root certificate ARN"),
            ("subnet_ids", "list(string)", "Associated subnet IDs"),
            ("security_group_ids", "list(string)", "Endpoint security group IDs"),
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
