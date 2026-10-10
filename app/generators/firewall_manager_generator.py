from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.organization_delegation import firewall_preconditions
from app.models.input_models.firewall_manager_config import FirewallManagerConfig
from app.models.ir_models import ResourceInstanceIR
from app.models.organization_delegation import DELEGATION_BY_SERVICE


class FirewallManagerGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, FirewallManagerConfig)
        attrs = {"account_id": Expr("var.account_id")}
        if config._organization_delegation:
            attrs["lifecycle"] = {
                "precondition": firewall_preconditions(
                    DELEGATION_BY_SERVICE[instance.service_type]
                )
            }
        return self._r.render_resource(
            "aws_fms_admin_account",
            instance.name,
            attrs,
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
