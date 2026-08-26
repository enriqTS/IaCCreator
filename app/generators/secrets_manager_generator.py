"""Terraform generator for AWS Secrets Manager secrets."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.secrets_manager_config import SecretsManagerConfig
from app.models.ir_models import ResourceInstanceIR


class SecretsManagerGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, SecretsManagerConfig)
        attrs = {
            "name": instance.name,
            "recovery_window_in_days": Expr("var.recovery_window_in_days"),
        }
        if config.description is not None:
            attrs["description"] = Expr("var.description")
        if config.kms_key_id is not None:
            attrs["kms_key_id"] = Expr("var.kms_key_id")
        return self._r.render_resource(
            "aws_secretsmanager_secret", instance.name, attrs
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        config = get_typed_config(instance, SecretsManagerConfig)
        parts = [
            self._r.render_variable(
                "recovery_window_in_days", "number", "Deletion recovery window"
            )
        ]
        if config.description is not None:
            parts.append(
                self._r.render_variable("description", "string", "Secret description")
            )
        if config.kms_key_id is not None:
            parts.append(
                self._r.render_variable("kms_key_id", "string", "KMS key ARN or ID")
            )
        return "\n".join(parts)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_secretsmanager_secret.{instance.name}"
        return "\n".join(
            [
                self._r.render_output("secret_id", f"{ref}.id", "Secret ID"),
                self._r.render_output("secret_arn", f"{ref}.arn", "Secret ARN"),
            ]
        )
