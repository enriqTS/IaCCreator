from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.transfer_family_config import TransferFamilyConfig
from app.models.ir_models import ResourceInstanceIR


class TransferFamilyGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TransferFamilyConfig)
        return self._r.render_resource(
            "aws_transfer_server",
            instance.name,
            {
                "protocols": Expr("var.protocols"),
                "endpoint_type": Expr("var.endpoint_type"),
                "identity_provider_type": Expr("var.identity_provider_type"),
                "force_destroy": Expr("var.force_destroy"),
                "tags": Expr("var.tags"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, TransferFamilyConfig)
        fields = [
            ("protocols", "list(string)", "Enabled transfer protocols"),
            ("endpoint_type", "string", "Server endpoint type"),
            ("identity_provider_type", "string", "Identity provider type"),
            ("force_destroy", "bool", "Force server deletion"),
            ("tags", "map(string)", "Server tags"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_transfer_server.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("server_id", f"{ref}.id", "Transfer server ID"),
                self._r.render_output(
                    "server_arn", f"{ref}.arn", "Transfer server ARN"
                ),
                self._r.render_output(
                    "server_endpoint", f"{ref}.endpoint", "Transfer server endpoint"
                ),
            ]
        )
