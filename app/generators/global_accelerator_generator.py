from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.global_accelerator_config import GlobalAcceleratorConfig
from app.models.ir_models import ResourceInstanceIR


class GlobalAcceleratorGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, GlobalAcceleratorConfig)
        return self._r.render_resource(
            "aws_globalaccelerator_accelerator",
            instance.name,
            {
                "name": Expr("var.accelerator_name"),
                "enabled": Expr("var.enabled"),
                "ip_address_type": Expr("var.ip_address_type"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, GlobalAcceleratorConfig)
        fields = [
            ("accelerator_name", "string", "Accelerator name"),
            ("enabled", "bool", "Enable accelerator"),
            ("ip_address_type", "string", "IP address type"),
            ("tags", "map(string)", "Accelerator tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_globalaccelerator_accelerator.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("accelerator_id", f"{ref}.id", "Accelerator ID"),
                self._r.render_output(
                    "accelerator_arn", f"{ref}.arn", "Accelerator ARN"
                ),
                self._r.render_output(
                    "dns_name", f"{ref}.dns_name", "Accelerator DNS name"
                ),
            ]
        )
