"""Terraform generator for AWS KMS keys."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.kms_config import KmsConfig
from app.models.ir_models import ResourceInstanceIR


class KmsGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, KmsConfig)
        parts = [
            self._r.render_resource(
                "aws_kms_key",
                instance.name,
                {
                    "description": Expr("var.description"),
                    "deletion_window_in_days": Expr("var.deletion_window_in_days"),
                    "enable_key_rotation": Expr("var.enable_key_rotation"),
                    "multi_region": Expr("var.multi_region"),
                },
            )
        ]
        if config.alias is not None:
            parts.append(
                self._r.render_resource(
                    "aws_kms_alias",
                    instance.name,
                    {
                        "name": Expr('"alias/${var.alias}"'),
                        "target_key_id": Expr(f"aws_kms_key.{instance.name}.key_id"),
                    },
                )
            )
        return "\n".join(parts)

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, KmsConfig)
        parts = [
            self._r.render_variable("description", "string", "Key description"),
            self._r.render_variable(
                "deletion_window_in_days", "number", "Deletion waiting period"
            ),
            self._r.render_variable(
                "enable_key_rotation", "bool", "Enable key rotation"
            ),
            self._r.render_variable(
                "multi_region", "bool", "Create a multi-Region key"
            ),
        ]
        if config.alias is not None:
            parts.append(self._r.render_variable("alias", "string", "Key alias"))
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_kms_key.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("key_id", f"{ref}.key_id", "KMS key ID"),
                self._r.render_output("key_arn", f"{ref}.arn", "KMS key ARN"),
            ]
        )
