from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.guardduty_config import GuardDutyConfig
from app.models.ir_models import ResourceInstanceIR


class GuardDutyGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, GuardDutyConfig)
        return self._r.render_resource(
            "aws_guardduty_detector",
            instance.name,
            {
                "enable": Expr("var.enabled"),
                "finding_publishing_frequency": Expr(
                    "var.finding_publishing_frequency"
                ),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, GuardDutyConfig)
        fields = [
            ("enabled", "bool", "Enable GuardDuty"),
            ("finding_publishing_frequency", "string", "Finding frequency"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_guardduty_detector.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "detector_id", f"{ref}.id", "GuardDuty detector ID"
                ),
            ]
        )
