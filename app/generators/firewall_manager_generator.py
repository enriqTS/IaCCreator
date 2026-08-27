from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.firewall_manager_config import FirewallManagerConfig
from app.models.ir_models import ResourceInstanceIR


class FirewallManagerGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, FirewallManagerConfig)
        return self._r.render_resource(
            "aws_fms_admin_account",
            instance.name,
            {
                "account_id": Expr("var.account_id"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, FirewallManagerConfig)
        fields = [
            ("account_id", "string", "Administrator account ID"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_fms_admin_account.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "administrator_account_id",
                    f"{ref}.id",
                    "Firewall Manager administrator account ID",
                ),
            ]
        )
