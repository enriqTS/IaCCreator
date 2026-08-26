"""Terraform generator for Amazon QuickSight namespaces."""

from app.generators.base import get_typed_config
from app.generators.hcl_renderer import Expr, HCLRenderer
from app.models.input_models.quicksight_config import QuickSightConfig
from app.models.ir_models import ResourceInstanceIR


class QuickSightGenerator:
    def __init__(self) -> None:
        self._r = HCLRenderer()

    def generate_resource_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, QuickSightConfig)
        return self._r.render_resource(
            "aws_quicksight_namespace",
            instance.name,
            {
                "namespace": Expr("var.namespace_name"),
                "aws_account_id": Expr("var.aws_account_id"),
                "identity_store": Expr("var.identity_store"),
            },
        )

    def generate_variables_tf(self, instance: ResourceInstanceIR) -> str:
        get_typed_config(instance, QuickSightConfig)
        fields = [
            ("namespace_name", "string", "QuickSight namespace name"),
            ("aws_account_id", "string", "AWS account ID"),
            ("identity_store", "string", "Namespace identity store"),
        ]
        return "\n".join(self._r.render_variable(*field) for field in fields)

    def generate_outputs_tf(self, instance: ResourceInstanceIR) -> str:
        ref = f"aws_quicksight_namespace.{instance.name}"
        return "\n".join(
            [
                self._r.render_output(
                    "namespace_arn", f"{ref}.arn", "QuickSight namespace ARN"
                ),
                self._r.render_output(
                    "namespace_name", f"{ref}.namespace", "QuickSight namespace name"
                ),
            ]
        )
