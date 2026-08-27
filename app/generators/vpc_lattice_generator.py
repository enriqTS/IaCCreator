from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.vpc_lattice_config import VpcLatticeConfig
from app.models.ir_models import ResourceInstanceIR


class VpcLatticeGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, VpcLatticeConfig)
        return self._r.render_resource(
            "aws_vpclattice_service_network",
            instance.name,
            {
                "name": Expr("var.service_network_name"),
                "auth_type": Expr("var.auth_type"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, VpcLatticeConfig)
        fields = [
            ("service_network_name", "string", "Service network name"),
            ("auth_type", "string", "Authentication type"),
            ("tags", "map(string)", "Service network tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_vpclattice_service_network.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "service_network_id", f"{ref}.id", "Service network ID"
                ),
                self._r.render_output(
                    "service_network_arn", f"{ref}.arn", "Service network ARN"
                ),
            ]
        )
