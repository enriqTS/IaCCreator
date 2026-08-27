from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.macie_config import MacieConfig
from app.models.ir_models import ResourceInstanceIR


class MacieGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, MacieConfig)
        return self._r.render_resource(
            "aws_macie2_account",
            instance.name,
            {
                "status": Expr("var.status"),
                "finding_publishing_frequency": Expr(
                    "var.finding_publishing_frequency"
                ),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, MacieConfig)
        fields = [
            ("status", "string", "Macie status"),
            ("finding_publishing_frequency", "string", "Finding frequency"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_macie2_account.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "macie_account_id", f"{ref}.id", "Macie account ID"
                ),
            ]
        )
