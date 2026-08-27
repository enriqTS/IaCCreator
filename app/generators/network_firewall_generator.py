from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.network_firewall_config import NetworkFirewallConfig
from app.models.ir_models import ResourceInstanceIR


class NetworkFirewallGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, NetworkFirewallConfig)
        return self._r.render_resource(
            "aws_networkfirewall_firewall",
            instance.name,
            {
                "name": Expr("var.firewall_name"),
                "vpc_id": Expr("var.vpc_id"),
                "firewall_policy_arn": Expr("var.firewall_policy_arn"),
                "subnet_mapping": {"subnet_id": Expr("var.subnet_id")},
                "delete_protection": Expr("var.delete_protection"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, NetworkFirewallConfig)
        fields = [
            ("firewall_name", "string", "Firewall name"),
            ("vpc_id", "string", "VPC ID"),
            ("subnet_id", "string", "Firewall subnet ID"),
            ("firewall_policy_arn", "string", "Firewall policy ARN"),
            ("delete_protection", "bool", "Delete protection"),
            ("tags", "map(string)", "Firewall tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_networkfirewall_firewall.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("firewall_id", f"{ref}.id", "Firewall ID"),
                self._r.render_output("firewall_arn", f"{ref}.arn", "Firewall ARN"),
            ]
        )
