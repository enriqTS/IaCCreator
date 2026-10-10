from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.generators.organization_delegation import CALLER, precondition
from app.models.input_models.inspector_config import InspectorConfig
from app.models.ir_models import ResourceInstanceIR


class InspectorGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, InspectorConfig)
        attrs = {
            "account_ids": Expr("var.account_ids"),
            "resource_types": Expr("var.resource_types"),
        }
        if config._organization_delegation:
            attrs["account_ids"] = Expr(
                f"length(var.account_ids) == 0 ? [{CALLER}] : var.account_ids"
            )
            attrs["lifecycle"] = {
                "precondition": [
                    precondition(
                        f"(length(var.account_ids) == 0 || toset(var.account_ids) == toset([{CALLER}])) && length(var.resource_types) > 0",
                        "Connected Inspector enables only the management account, with at least one scan type.",
                    )
                ]
            }
        return self._r.render_resource(
            "aws_inspector2_enabler",
            instance.name,
            attrs,
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, InspectorConfig)
        fields = [
            ("account_ids", "list(string)", "AWS account IDs"),
            ("resource_types", "list(string)", "Scan resource types"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_inspector2_enabler.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "enabler_id", f"{ref}.id", "Inspector enabler ID"
                ),
            ]
        )
