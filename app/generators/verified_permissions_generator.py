from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.verified_permissions_config import (
    VerifiedPermissionsConfig,
)
from app.models.ir_models import ResourceInstanceIR


class VerifiedPermissionsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, VerifiedPermissionsConfig)
        return self._r.render_resource(
            "aws_verifiedpermissions_policy_store",
            instance.name,
            {
                "description": Expr("var.description"),
                "validation_settings": {"mode": Expr("var.validation_mode")},
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, VerifiedPermissionsConfig)
        fields = [
            ("description", "string", "Policy store description"),
            ("validation_mode", "string", "Cedar validation mode"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_verifiedpermissions_policy_store.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "policy_store_id", f"{ref}.policy_store_id", "Policy store ID"
                ),
                self._r.render_output(
                    "policy_store_arn", f"{ref}.arn", "Policy store ARN"
                ),
            ]
        )
